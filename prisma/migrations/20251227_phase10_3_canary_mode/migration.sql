-- AlterTable: Add canary_enabled to ExternalApiKey
ALTER TABLE "external_api_keys" ADD COLUMN "canary_enabled" BOOLEAN NOT NULL DEFAULT false;

-- Create index for canary lookups
CREATE INDEX "external_api_keys_canary_idx" ON "external_api_keys"("canary_enabled") WHERE "is_active" = true;
