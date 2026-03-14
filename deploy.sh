#!/usr/bin/env bash
set -euo pipefail

# ────────────────────────────────────────────────────────────────────────────
# deploy.sh — Deploy or update the Eclipse Commentator SPA stack
#
# Usage:
#   ./deploy.sh                                    # deploy without custom domain
#   ./deploy.sh my-stack us-west-2 production      # custom stack, region, profile
#
# Environment variables (optional):
#   DOMAIN_NAME      — custom domain (e.g. eclipse.klp.keycore.cloud)
#   HOSTED_ZONE_NAME — Route 53 hosted zone (default: klp.keycore.cloud)
#
# Examples:
#   # Deploy with custom domain (uses default hosted zone)
#   DOMAIN_NAME=eclipse.klp.keycore.cloud ./deploy.sh
#
#   # Deploy with custom domain and explicit hosted zone
#   DOMAIN_NAME=eclipse.example.com HOSTED_ZONE_NAME=example.com ./deploy.sh
#
# Prerequisites:
#   - AWS CLI configured (aws configure / SSO / env vars)
#   - Sufficient IAM permissions for CloudFormation, S3, CloudFront,
#     IAM, ACM, Route 53
# ────────────────────────────────────────────────────────────────────────────

STACK_NAME="${1:-eclipse}"
REGION="${2:-eu-west-1}"
PROFILE="${3:-sandbox}"
DOMAIN_NAME="${DOMAIN_NAME:-}"
HOSTED_ZONE_NAME="${HOSTED_ZONE_NAME:-klp.keycore.cloud}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE="${SCRIPT_DIR}/template.yaml"
SPA_FILE="${SCRIPT_DIR}/eclipse.html"

# ── Preflight check ───────────────────────────────────────────────────────
if [[ ! -f "${SPA_FILE}" ]]; then
  echo "ERROR: ${SPA_FILE} not found" >&2
  exit 1
fi

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Eclipse Commentator SPA — AWS Deployment                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "  Stack:    ${STACK_NAME}"
echo "  Region:   ${REGION}"
echo "  Profile:  ${PROFILE}"
echo "  Template: ${TEMPLATE}"
echo "  SPA file: ${SPA_FILE} ($(du -h "${SPA_FILE}" | cut -f1) )"
if [[ -n "${DOMAIN_NAME}" ]]; then
  echo "  Domain:   ${DOMAIN_NAME}"
  echo "  Zone:     ${HOSTED_ZONE_NAME}"
fi
echo ""

# ── Step 1: Validate template ──────────────────────────────────────────────
echo "→ Validating CloudFormation template..."
aws cloudformation validate-template \
  --template-body "file://${TEMPLATE}" \
  --region "${REGION}" \
  --profile "${PROFILE}" \
  --output text > /dev/null
echo "  ✓ Template valid"
echo ""

# ── Step 2: Build parameter overrides ─────────────────────────────────────
PARAM_OVERRIDES="StackPrefix=${STACK_NAME}"
if [[ -n "${DOMAIN_NAME}" ]]; then
  PARAM_OVERRIDES="${PARAM_OVERRIDES} DomainName=${DOMAIN_NAME} HostedZoneName=${HOSTED_ZONE_NAME}"
fi

# ── Step 3: Deploy / update stack ─────────────────────────────────────────
if [[ -n "${DOMAIN_NAME}" ]]; then
  echo "→ Deploying stack with custom domain (certificate provisioning may take 5-10 minutes)..."
else
  echo "→ Deploying stack (this may take 5-10 minutes on first run)..."
fi
aws cloudformation deploy \
  --template-file "${TEMPLATE}" \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --profile "${PROFILE}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides ${PARAM_OVERRIDES} \
  --no-fail-on-empty-changeset
echo "  ✓ Stack deployed"
echo ""

# ── Step 4: Get outputs ──────────────────────────────────────────────────
echo "→ Reading stack outputs..."
OUTPUTS=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --profile "${PROFILE}" \
  --query "Stacks[0].Outputs" \
  --output json)

BUCKET=$(echo "${OUTPUTS}" | python3 -c "import sys,json; print(next(o['OutputValue'] for o in json.load(sys.stdin) if o['OutputKey']=='SpaBucketName'))")
CF_URL=$(echo "${OUTPUTS}" | python3 -c "import sys,json; print(next(o['OutputValue'] for o in json.load(sys.stdin) if o['OutputKey']=='CloudFrontUrl'))")
CF_DIST=$(echo "${OUTPUTS}" | python3 -c "import sys,json; print(next(o['OutputValue'] for o in json.load(sys.stdin) if o['OutputKey']=='CloudFrontDistributionId'))")
DASH_URL=$(echo "${OUTPUTS}" | python3 -c "import sys,json; print(next((o['OutputValue'] for o in json.load(sys.stdin) if o['OutputKey']=='DashboardUrl'), ''))")

echo "  Bucket:       ${BUCKET}"
echo "  CloudFront:   ${CF_URL}"
echo "  Distribution: ${CF_DIST}"
if [[ -n "${DASH_URL}" ]]; then
  echo "  Custom URL:   ${DASH_URL}"
fi
echo ""

# ── Step 5: Upload SPA to S3 ─────────────────────────────────────────────
# Upload as index.html (CloudFront DefaultRootObject) and also as eclipse.html
echo "→ Uploading eclipse.html to S3..."
aws s3 cp "${SPA_FILE}" "s3://${BUCKET}/index.html" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache, no-store, must-revalidate" \
  --region "${REGION}" \
  --profile "${PROFILE}"
aws s3 cp "${SPA_FILE}" "s3://${BUCKET}/eclipse.html" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache, no-store, must-revalidate" \
  --region "${REGION}" \
  --profile "${PROFILE}"
echo "  ✓ Uploaded as index.html and eclipse.html"
echo ""

# ── Step 6: Invalidate CloudFront cache ──────────────────────────────────
echo "→ Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id "${CF_DIST}" \
  --paths "/*" \
  --profile "${PROFILE}" \
  --output text > /dev/null
echo "  ✓ Invalidation created (may take 1-2 minutes to propagate)"
echo ""

# ── Done ─────────────────────────────────────────────────────────────────
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Deployment complete!                                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
if [[ -n "${DASH_URL}" ]]; then
  echo "  Eclipse SPA: ${DASH_URL}"
else
  echo "  Eclipse SPA: ${CF_URL}"
fi
echo ""
echo "  To update just the SPA (no infra changes):"
echo "    aws s3 cp eclipse.html s3://${BUCKET}/index.html --content-type 'text/html; charset=utf-8' --cache-control 'no-cache' --profile ${PROFILE}"
echo "    aws s3 cp eclipse.html s3://${BUCKET}/eclipse.html --content-type 'text/html; charset=utf-8' --cache-control 'no-cache' --profile ${PROFILE}"
echo "    aws cloudfront create-invalidation --distribution-id ${CF_DIST} --paths '/*' --profile ${PROFILE}"
echo ""
