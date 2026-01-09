from typing import List, Dict
from fastapi import HTTPException, UploadFile
from PIL import Image
import io
import uuid
import boto3
from datetime import datetime


class ImageStorageService:
    """Service for handling home image uploads with dynamic limits"""
    
    # Image limits based on room count
    IMAGE_LIMITS = {
        1: 5,   # Studio/1BR: 5 images max
        2: 6,   # 2BR: 6 images max  
        3: 8,   # 3BR: 8 images max
        4: 10,  # 4BR: 10 images max
        5: 12,  # 5+BR: 12 images max
    }
    
    # Allowed file types
    ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    
    # Max file size (5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024
    
    # Image dimensions
    MAX_WIDTH = 2048
    MAX_HEIGHT = 2048
    
    def __init__(self, bucket_name: str = None):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3') if bucket_name else None
    
    def get_image_limit(self, room_count: int) -> int:
        """Get maximum allowed images based on room count"""
        if room_count >= 5:
            return self.IMAGE_LIMITS[5]
        return self.IMAGE_LIMITS.get(room_count, 5)
    
    def validate_image_file(self, file: UploadFile) -> bool:
        """Validate a single image file"""
        # Check file type
        if file.content_type not in self.ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type:{file.content_type}. Allowed types are {','.join(self.ALLOWED_TYPES)}"
            )

        # Check file size
        if file.size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {self.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        return True
    
    def validate_image_count(self, current_count: int, new_count: int, room_count: int) -> bool:
        """Validate total image count doesn't exceed limit"""
        max_image = self.get_image_limit(room_count)
        if current_count +new_count >max_image:
            raise HTTPException(
                status_code =400,
                detail =f"Image limit exceeds for {room_count} room's home.Max allowed images:{max_image}"
            )

    
    def optimize_image(self, file_content: bytes, max_width: int = None, max_height: int = None) -> bytes:
        """Optimize image size and quality for cost efficiency"""
        max_width = max_width or self.MAX_WIDTH
        max_height = max_height or self.MAX_HEIGHT
        
        # Open image
        image = Image.open(io.BytesIO(file_content))
        
        # Convert to RGB if necessary (for JPEG)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        # Resize if too large
        if image.width > max_width or image.height > max_height:
            image.thumbnail((max_width, max_height))
        
        #Save optimized image
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue()
    
    def generate_s3_key(self, user_id: int, home_id: int, filename: str) -> str:
        """Generate organized S3 key for the image"""
        # Create unique filename to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_extension = filename.split('.')[-1].lower()
        
       
        s3_key = f"homes/user_{user_id}/home_{home_id}/{timestamp}_{unique_id}.{file_extension}"
        return s3_key
    
    def upload_to_s3(self, s3_key: str, image_content: bytes) -> str:
        """Upload image to S3 and return URL"""
        if not self.s3_client or not self.bucket_name:
            raise HTTPException(status_code=500, detail="S3 not configured")
        
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_content,
                ContentType="image/jpeg"
            )
            
            # Return public URL
            url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            return url
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")
    
    def delete_from_s3(self, s3_key: str) -> bool:
        """Delete image from S3"""
        if not self.s3_client or not self.bucket_name:
            return False
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except Exception:
            return False
    
    def process_and_upload_image(self, file: UploadFile, user_id: int, home_id: int) -> str:
        """Complete process: validate, optimize, and upload image"""
        # Validate file
        self.validate_image_file(file)
        
        # Read and optimize image
        file_content = file.file.read()
        optimized_content = self.optimize_image(file_content)
        
        # Generate S3 key and upload
        s3_key = self.generate_s3_key(user_id, home_id, file.filename)
        url = self.upload_to_s3(s3_key, optimized_content)
        
        # Reset file pointer
        file.file.seek(0)
        
        return url


# Create global instance
image_storage = ImageStorageService()