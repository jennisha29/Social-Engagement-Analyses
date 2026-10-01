# Student-Safe AWS Plan for SupplyFlow

This project is designed to be impressive without requiring paid AWS deployment. Use the local demo first, then move to AWS only inside a student-safe environment.

## Safest Recommendation

Use this order:

1. Local laptop demo
2. AWS Educate free labs
3. AWS Academy learner lab, if your school provides it
4. AWS Free Tier only after cost guardrails are set
5. Full AWS deployment only when you are ready to monitor and clean up resources

## Option 1: Local Demo, No AWS Cost

This is the recommended portfolio path.

```bash
cd /Users/jennishachristinamartin/Desktop/SupplyFlow_AWS_ETL
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dashboard]"
supplyflow-generate --rows 2500
supplyflow-curate
supplyflow-validate
streamlit run src/supplyflow/dashboard.py
```

Result:

- no AWS account required
- no cloud charges
- full ETL pipeline logic
- nine-table warehouse output
- dashboard-ready marts
- portfolio documentation

## Option 2: AWS Educate, Best Student Cloud Practice

AWS Educate is the safest cloud-learning option for students because it provides free learning and hands-on labs without requiring a credit card.

Use AWS Educate to practice:

- S3 basics
- cloud storage labs
- compute labs
- database labs
- cost-estimation labs

Recommendation: use AWS Educate for learning AWS services, while keeping this SupplyFlow project local unless your lab explicitly supports Glue and Redshift.

Official link: https://aws.amazon.com/education/awseducate/

## Option 3: AWS Academy, If Your School Offers It

AWS Academy is good if your school gives you a learner lab or sandbox.

Use AWS Academy when:

- your course provides credits or lab access
- the lab automatically shuts down resources
- you are working under a classroom sandbox

Recommendation: ask your professor or school IT department whether AWS Academy Learner Lab is available.

Official link: https://aws.amazon.com/training/awsacademy/

## Option 4: AWS Free Tier, Use Carefully

AWS Free Tier can be student-friendly, but it requires attention.

AWS says new Free Tier accounts can receive credits and that the Free plan does not incur charges unless you upgrade to a Paid plan or activate paid-only services. However, a full SupplyFlow deployment may need services that are not ideal for the Free plan, especially Glue and Redshift.

Official link: https://aws.amazon.com/free/

## Cost Guardrails Before Any AWS Deployment

Do these before creating resources:

1. Stay on the AWS Free plan if possible.
2. Create an AWS Budget alert.
3. Set the alert threshold very low, such as `$1` or `$5`.
4. Use a small dataset only.
5. Avoid Redshift until you are ready.
6. Avoid running Glue jobs repeatedly.
7. Delete all test resources after the demo.

AWS Budgets monitoring and notifications can be used free of charge. Avoid advanced action-enabled budgets beyond the free allowance.

Official link: https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/

## Services to Avoid Until You Are Ready

Be cautious with:

- Redshift Serverless
- provisioned Redshift clusters
- long-running Glue jobs
- repeated Glue crawlers
- large S3 uploads
- NAT gateways
- paid marketplace products

For this project, Redshift is the biggest cost risk if left active.

## Student-Friendly Project Strategy

For your portfolio, say:

> Built and validated the full ETL pipeline locally with AWS-ready Lambda, Glue, S3, and Redshift artifacts. Designed the deployment for AWS, with student-safe local execution to avoid unnecessary cloud cost.

This is honest, technically strong, and cost-aware.

## When to Deploy for Real

Only deploy to AWS when you can answer yes to all of these:

- I have a budget alert configured.
- I know which AWS region I am using.
- I know how to delete S3 buckets, Glue jobs, crawlers, Lambda functions, and Redshift resources.
- I am using the smallest dataset.
- I have time to clean everything up immediately after testing.

## Cleanup Checklist

After any AWS test:

- Stop or delete Redshift resources.
- Delete Glue crawlers.
- Delete Glue jobs.
- Delete Lambda functions.
- Empty and delete S3 buckets.
- Check CloudWatch logs.
- Check Billing and Cost Management.
- Confirm the budget dashboard shows no unexpected activity.
