from django.conf import settings
from minio import Minio
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework.response import *
from rest_framework import status

def process_file_upload(file_object: InMemoryUploadedFile, client, image_name, folder, bucket = settings.AWS_STORAGE_BUCKET_NAME):
    try:
        fname = f"{folder}/{image_name}"
        objects = client.list_objects(bucket)
        if fname in objects:
            client.remove_object(bucket, fname)
        client.put_object(bucket, fname, file_object, file_object.size)
        return f"http://localhost:9000/{bucket}/{folder}/{image_name}"
    except Exception as e:
        return {"error": str(e)}
    
def add_pic(object, pic, folder):
    client = Minio(           
            endpoint=settings.AWS_S3_ENDPOINT_URL,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
            secure=settings.MINIO_USE_SSL
    )
    i = object.id
    img_obj_name = f"{i}.png"

    if not pic:
        return Response({"error": "Нет файла для изображения."})
    result = process_file_upload(pic, client, img_obj_name, folder)

    if 'error' in result:
        return Response(result)

    object.image = result
    object.save()

    return Response(result)

def del_pic(object, folder, bucket = settings.AWS_STORAGE_BUCKET_NAME):
    client = Minio(           
            endpoint=settings.AWS_S3_ENDPOINT_URL,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
            secure=settings.MINIO_USE_SSL
    )
    i = object.id
    img_obj_name = f"{i}.png"
    try:
        fname = f"{folder}/{img_obj_name}"
        client.remove_object(bucket, fname)
        return Response({"success": "deleted"}, status.HTTP_204_NO_CONTENT)
    except Exception as e:
        return Response({"error": str(e)})

