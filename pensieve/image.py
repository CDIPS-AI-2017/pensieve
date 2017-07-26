from io import BytesIO
import json
import os
import requests
import urllib
import uuid

# pillow
from PIL import Image
# boto3 for AWS
import boto3


def upload_image(url, bucket='gx42-image-source'):
    """ Save image to S3 bucket for later retrieval

    Args:
        url: url of image to store
        bucket: str S3 bucket to save key

    Returns:
        success: boolean indicating if upload was successful
        full_key_name: uuid  to store in imageURL
            eg. 64C27228-0004-4C60-8B7E-95702956700F

    Security Defaults to ~/.aws/credential
    """
    imguid = str(uuid.uuid4()).upper()
    try:
        s3 = boto3.resource('s3')
        resp = requests.get(url)
        dat = urllib.request.urlopen(resp.url)
        img = Image.open(dat)
        out_im2 = BytesIO()
        img.save(out_im2, 'JPEG', optimize=True, progressive=True)
        out_im2.seek(0)
        full_key_name = imguid
        s3.Bucket(bucket).put_object(
            Key=full_key_name,
            Body=out_im2,
            ACL='public-read',
            ContentType='image/jpg',
        )
        return True, full_key_name
    except Exception as e:
        print('upload_image ERROR', e)
        return False, e