# media/services/storage_s3.py
import os
import boto3
from botocore.config import Config
from typing import BinaryIO
from .storage_base import Storage

class S3Storage(Storage):
    def __init__(self, bucket: str, region: str, prefix: str = "media/"):
        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/"
        self.s3 = boto3.client("s3", config=Config(s3={"addressing_style": "virtual"}), region_name=region)

    def _k(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def save(self, key: str, stream: BinaryIO, size: int, content_type: str) -> None:
        self.s3.upload_fileobj(
            Fileobj=stream,
            Bucket=self.bucket,
            Key=self._k(key),
            ExtraArgs={"ContentType": content_type, "StorageClass": "STANDARD_IA"}
        )

    def open(self, key: str) -> BinaryIO:
        return self.s3.get_object(Bucket=self.bucket, Key=self._k(key))["Body"]

    def exists(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=self._k(key))
            return True
        except Exception:
            return False

    def url(self, key: str, expires: int = 3600) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": self._k(key)},
            ExpiresIn=expires
        )

    @staticmethod
    def presign_post(bucket: str, key: str, expires: int = 3600, max_size: int = 20*1024*1024*1024):
        s3 = boto3.client("s3")
        fields = {"acl": "bucket-owner-full-control"}
        conditions = [["starts-with", "$key", key.rsplit("/",1)[0] + "/"],
                      ["content-length-range", 1, max_size]]
        return s3.generate_presigned_post(Bucket=bucket, Key=key, Fields=fields, Conditions=conditions, ExpiresIn=expires)
