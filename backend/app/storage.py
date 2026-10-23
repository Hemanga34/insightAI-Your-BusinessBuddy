from pathlib import Path

from app.config import get_settings


def save_file(key: str, source: Path):
    settings = get_settings()
    if settings.storage_backend == "s3":
        import boto3

        boto3.client("s3", region_name=settings.aws_region).upload_file(
            str(source),
            settings.s3_bucket,
            key,
            ExtraArgs={"ServerSideEncryption": "AES256"},
        )
    else:
        target = settings.upload_dir / key
        target.parent.mkdir(parents=True, exist_ok=True)
        source.replace(target)


def materialize(key: str, target: Path) -> Path:
    settings = get_settings()
    if settings.storage_backend == "local":
        return settings.upload_dir / key
    import boto3

    boto3.client("s3", region_name=settings.aws_region).download_file(
        settings.s3_bucket,
        key,
        str(target),
    )
    return target


def delete_file(key: str):
    settings = get_settings()
    if settings.storage_backend == "s3":
        import boto3

        boto3.client("s3", region_name=settings.aws_region).delete_object(
            Bucket=settings.s3_bucket,
            Key=key,
        )
    else:
        (settings.upload_dir / key).unlink(missing_ok=True)
