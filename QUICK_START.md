# 🚀 Quick Start: Deploy to AWS Lambda

## ✅ Pre-Deployment Checklist

- [ ] AWS Account created
- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Python 3.13 installed
- [ ] RDS PostgreSQL database created
- [ ] AWS Cognito User Pool set up

## 🎯 Quick Deployment (5 Steps)

### 1️⃣ Build Deployment Package

```bash
chmod +x deploy_lambda.sh
./deploy_lambda.sh
```

This creates `ezdoc-lambda.zip`

### 2️⃣ Create Lambda Function

**Option A: AWS Console**

- Go to Lambda Console → Create function
- Name: `ezdoc-api`
- Runtime: Python 3.13
- Upload `ezdoc-lambda.zip`
- Handler: `lambda_handler.handler`

**Option B: AWS CLI**

```bash
aws lambda create-function \
  --function-name ezdoc-api \
  --runtime python3.13 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-role \
  --handler lambda_handler.handler \
  --zip-file fileb://ezdoc-lambda.zip \
  --timeout 30 \
  --memory-size 512
```

### 3️⃣ Configure Environment Variables

```bash
chmod +x configure_lambda_env.sh
./configure_lambda_env.sh
```

Or manually set in Lambda console:

- `DATABASE_URL` - Your RDS PostgreSQL connection string
- `API_URL` - Your API Gateway URL
- `SECRET_KEY` - Random secure key
- `COGNITO_REGION` - e.g., us-east-1
- `COGNITO_USER_POOL_ID` - Your pool ID
- `COGNITO_APP_CLIENT_ID` - Your client ID
- `ENV` - production

### 4️⃣ Create API Gateway

- Go to API Gateway Console
- Create HTTP API
- Add Lambda integration: `ezdoc-api`
- Route: `ANY /{proxy+}`
- Deploy

### 5️⃣ Test

```bash
curl https://YOUR_API_GATEWAY_URL/
```

Expected: `{"message": "Welcome to the Ezdoc API!"}`

## 📚 Full Documentation

See [AWS_LAMBDA_DEPLOYMENT.md](AWS_LAMBDA_DEPLOYMENT.md) for complete step-by-step guide.

## 🔄 Update Deployed Function

```bash
./deploy_lambda.sh
aws lambda update-function-code \
  --function-name ezdoc-api \
  --zip-file fileb://ezdoc-lambda.zip
```

## 🐛 Troubleshooting

**View logs:**

```bash
aws logs tail /aws/lambda/ezdoc-api --follow
```

**Common issues:**

- Timeout → Increase timeout in Lambda settings
- Cannot connect to RDS → Check VPC and security groups
- Import errors → Rebuild package with `./deploy_lambda.sh`

## 📞 Key AWS Services

- **Lambda**: Runs your application
- **API Gateway**: Creates REST API endpoints
- **RDS**: PostgreSQL database
- **VPC**: Network isolation
- **CloudWatch**: Logs and monitoring

## 💡 Tips

- Start with 512MB memory, increase if needed
- Set timeout to 30 seconds minimum
- Enable CloudWatch Logs for debugging
- Use same VPC for Lambda and RDS
- Keep package size under 250MB unzipped

---

**Need help?** Check [AWS_LAMBDA_DEPLOYMENT.md](AWS_LAMBDA_DEPLOYMENT.md) for detailed instructions!
