import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadminpassword")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "contracts")

class S3StorageClient:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            self.s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
        except ClientError:
            try:
                self.s3_client.create_bucket(Bucket=S3_BUCKET_NAME)
            except Exception as e:
                print(f"Warning: Could not create bucket (MOCK MODE?): {e}")
        except Exception as e:
            print(f"Warning: Could not connect to S3 (MOCK MODE?): {e}")

    def upload_file(self, file_content: bytes, object_name: str) -> str:
        """Uploads a file to S3 and returns the object key."""
        self.s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_name,
            Body=file_content
        )
        return object_name

    def download_file(self, object_name: str) -> bytes:
        """Downloads a file from S3."""
        response = self.s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=object_name)
        return response['Body'].read()

    def get_presigned_url(self, object_name: str, expiration: int = 3600) -> Optional[str]:
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET_NAME, 'Key': object_name},
                ExpiresIn=expiration
            )
        except ClientError:
            return None
