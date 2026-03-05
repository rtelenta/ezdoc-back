# AWS Lambda Deployment Guide for ezdoc-back

This guide will walk you through deploying your FastAPI application to AWS Lambda step by step.

## 📋 Prerequisites

Before starting, ensure you have:

- [ ] AWS Account with appropriate permissions
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Python 3.13 installed locally
- [ ] PostgreSQL database (AWS RDS recommended)
- [ ] AWS Cognito User Pool set up

## 🏗️ Architecture Overview

```
API Gateway → Lambda Function → RDS PostgreSQL
                ↓
           AWS Cognito (Authentication)
```

---

## 📦 Step 1: Prepare Your Project

### 1.1 Install Deployment Dependencies

```bash
pip install mangum
```

### 1.2 Verify Files Created

Your project now has:

- ✅ `lambda_handler.py` - Lambda entry point
- ✅ `requirements.txt` - All dependencies
- ✅ `deploy_lambda.sh` - Deployment script

---

## 🗄️ Step 2: Set Up AWS RDS Database

### 2.1 Create PostgreSQL RDS Instance

1. Go to AWS RDS Console
2. Click "Create database"
3. Choose:
   - Engine: PostgreSQL
   - Template: Free tier (for testing) or Production
   - DB instance identifier: `ezdoc-db`
   - Master username: `ezdoc_admin`
   - Master password: (save this securely)
   - DB instance class: db.t3.micro (or larger)
   - Storage: 20 GB
   - VPC: Default VPC
   - Public access: No
   - VPC security group: Create new
   - Database name: `ezdoc`

4. Click "Create database" (takes 5-10 minutes)

### 2.2 Configure Security Group

1. After creation, click on your database
2. Under "Connectivity & security", click the VPC security group
3. Edit inbound rules:
   - Type: PostgreSQL
   - Port: 5432
   - Source: Lambda security group (create if needed)

### 2.3 Get Database Connection String

Format: `postgresql://username:password@endpoint:5432/database`

Example:

```
postgresql://ezdoc_admin:yourpassword@ezdoc-db.xxx.us-east-1.rds.amazonaws.com:5432/ezdoc
```

---

## 📦 Step 3: Create Lambda Deployment Package

### 3.1 Make Deploy Script Executable

```bash
chmod +x deploy_lambda.sh
```

### 3.2 Run Deployment Script

```bash
./deploy_lambda.sh
```

This creates `ezdoc-lambda.zip` containing your application and all dependencies.

**Important:** If the package is > 50MB (unzipped):

- You must use S3 for deployment (see Step 4b)
- Or use Lambda Layers for large dependencies

---

## 🚀 Step 4: Create Lambda Function

### Option A: AWS Console (Recommended for first time)

1. Go to AWS Lambda Console
2. Click "Create function"
3. Choose "Author from scratch"
4. Configure:
   - Function name: `ezdoc-api`
   - Runtime: Python 3.13
   - Architecture: x86_64
   - Permissions: Create new role with basic Lambda permissions

5. Click "Create function"

### Option B: AWS CLI

```bash
# Create IAM role first
aws iam create-role \
  --role-name ezdoc-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach basic execution policy
aws iam attach-role-policy \
  --role-name ezdoc-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create Lambda function
aws lambda create-function \
  --function-name ezdoc-api \
  --runtime python3.13 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/ezdoc-lambda-role \
  --handler lambda_handler.handler \
  --zip-file fileb://ezdoc-lambda.zip \
  --timeout 30 \
  --memory-size 512
```

---

## ⚙️ Step 5: Configure Lambda Function

### 5.1 Upload Code (Console)

1. In Lambda function page, scroll to "Code source"
2. Click "Upload from" → ".zip file"
3. Upload `ezdoc-lambda.zip`
4. Click "Save"

### 5.2 Set Handler

Under "Runtime settings":

- Handler: `lambda_handler.handler`

### 5.3 Configure Basic Settings

Under "Configuration" → "General configuration":

- Memory: **512 MB** (minimum, increase if needed)
- Timeout: **30 seconds** (increase for larger operations)
- Ephemeral storage: 512 MB

### 5.4 Set Environment Variables

Under "Configuration" → "Environment variables":

```
DATABASE_URL=postgresql://ezdoc_admin:password@your-rds-endpoint:5432/ezdoc
API_URL=https://your-api-gateway-url/prod
SECRET_KEY=your-secret-key-here
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_APP_CLIENT_ID=your-app-client-id
ENV=production
```

**Generate SECRET_KEY:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5.5 Configure VPC (For RDS Access)

Under "Configuration" → "VPC":

1. Edit VPC settings
2. Select the same VPC as your RDS instance
3. Select private subnets
4. Select security group that can access RDS
5. Save

**Note:** Lambda in VPC needs NAT Gateway for internet access.

---

## 🌐 Step 6: Set Up API Gateway

### 6.1 Create HTTP API (Recommended)

1. Go to API Gateway Console
2. Click "Create API"
3. Choose "HTTP API" → "Build"
4. Add integration:
   - Integration type: Lambda
   - Lambda function: ezdoc-api
   - API name: ezdoc-api
5. Configure routes:
   - Method: ANY
   - Resource path: `/{proxy+}`
6. Configure stages:
   - Stage name: `prod` or `$default`
   - Auto-deploy: Yes
7. Click "Create"

### 6.2 Get API Endpoint

After creation, you'll see:

```
Invoke URL: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
```

This is your API's base URL!

### 6.3 Update Environment Variable

Go back to Lambda → Environment variables:

- Update `API_URL` with your API Gateway URL

---

## 🗃️ Step 7: Run Database Migrations

### Option A: Local Migration (Recommended)

From your local machine with RDS access:

```bash
# Set database URL
export DATABASE_URL="postgresql://username:password@rds-endpoint:5432/ezdoc"

# Run migrations
alembic upgrade head
```

### Option B: Lambda Migration

Create a temporary script and invoke Lambda:

```python
# migration_script.py
import os
os.environ["DATABASE_URL"] = "your-rds-url"
from alembic import command
from alembic.config import Config
alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "revision")
```

---

## ✅ Step 8: Test Your Deployment

### 8.1 Test Root Endpoint

```bash
curl https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/
```

Expected response:

```json
{ "message": "Welcome to the Ezdoc API!" }
```

### 8.2 Test API Endpoints

```bash
# Test templates endpoint
curl https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/api/templates

# Test users endpoint
curl https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/api/users
```

### 8.3 Monitor Logs

```bash
aws logs tail /aws/lambda/ezdoc-api --follow
```

Or use CloudWatch Logs in AWS Console.

---

## 🔄 Step 9: Update Your Application

When you make changes:

```bash
# 1. Rebuild package
./deploy_lambda.sh

# 2. Update Lambda function
aws lambda update-function-code \
  --function-name ezdoc-api \
  --zip-file fileb://ezdoc-lambda.zip
```

---

## 🎯 Step 10: Production Optimization

### 10.1 Enable Lambda Insights (Monitoring)

```bash
aws lambda update-function-configuration \
  --function-name ezdoc-api \
  --layers arn:aws:lambda:us-east-1:580247275435:layer:LambdaInsightsExtension:14
```

### 10.2 Set Up CloudWatch Alarms

Monitor:

- Error rate
- Duration
- Throttles
- Concurrent executions

### 10.3 Enable Lambda Function URLs (Alternative to API Gateway)

```bash
aws lambda create-function-url-config \
  --function-name ezdoc-api \
  --auth-type NONE \
  --cors '{
    "AllowOrigins": ["*"],
    "AllowMethods": ["*"],
    "AllowHeaders": ["*"]
  }'
```

### 10.4 Optimize Cold Starts

- Use provisioned concurrency for consistent performance
- Minimize package size
- Use Lambda Layers for large dependencies

---

## 🛠️ Troubleshooting

### Issue: Lambda timeout

**Solution:** Increase timeout in Lambda configuration (max 15 minutes)

### Issue: Package too large

**Solutions:**

1. Use Lambda Layers
2. Remove unnecessary dependencies
3. Upload to S3 and reference from Lambda

### Issue: Cannot connect to RDS

**Solutions:**

1. Verify Lambda is in same VPC as RDS
2. Check security group rules
3. Verify RDS endpoint and credentials

### Issue: Module import errors

**Solution:** Ensure all dependencies are in requirements.txt and properly installed in package

---

## 📊 Cost Estimation

### AWS Lambda

- Free tier: 1M requests/month + 400,000 GB-seconds
- After: $0.20 per 1M requests + $0.0000166667 per GB-second

### API Gateway

- Free tier: 1M API calls/month (12 months)
- After: $1.00 per million requests

### RDS

- db.t3.micro: ~$15/month
- db.t3.small: ~$30/month

---

## 🔐 Security Best Practices

1. ✅ Use AWS Secrets Manager for sensitive data
2. ✅ Enable VPC for Lambda
3. ✅ Use IAM roles with least privilege
4. ✅ Enable API Gateway authentication
5. ✅ Use HTTPS only
6. ✅ Enable CloudWatch Logs encryption
7. ✅ Regular security audits

---

## 📚 Additional Resources

- [AWS Lambda Python](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html)
- [Mangum Documentation](https://mangum.io/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [AWS RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)

---

## 🆘 Need Help?

Check Lambda logs in CloudWatch:

```bash
aws logs tail /aws/lambda/ezdoc-api --follow
```

---

**🎉 Congratulations! Your FastAPI application is now running on AWS Lambda!**
