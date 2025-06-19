import os
import boto3
from PIL import Image

s3_client = boto3.client("s3")

INPUT_BUCKET = os.environ["INPUT_BUCKET"]
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
INPUT_KEY = os.environ["INPUT_KEY"]
OUTPUT_KEY = os.environ["OUTPUT_KEY"]
TEMP_DIR = "/tmp"

def main():
    input_path = os.path.join(TEMP_DIR, "input_image")
    output_path = os.path.join(TEMP_DIR, "thumbnail.jpg")

    print("Downloading from S3...")
    s3_client.download_file(INPUT_BUCKET, INPUT_KEY, input_path)

    print("Creating thumbnail...")
    with Image.open(input_path) as img:
        img.thumbnail((128, 128))
        img = img.convert("RGB")
        img.save(output_path, "JPEG")

    print("Uploading thumbnail to S3...")
    s3_client.upload_file(output_path, OUTPUT_BUCKET, OUTPUT_KEY)

    print("Thumbnail created and uploaded successfully!")

if __name__ == "__main__":
    main()
