from rest_framework import serializers

from pathlib import Path
from urllib.parse import quote_plus
import pymongo
import os
import environ
import logging

from .methods import upload_and_get_image_path, get_next_sequence
from .mongo_client import get_mongo_db, ConnectionFailure

env = environ.Env()
environ.Env.read_env(os.path.join(Path(__file__).resolve().parent.parent.parent, '.env'))
logger = logging.getLogger('web')
logger_file = logging.getLogger('file')


class CreateListSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        # pull the collection out of the child serializer's Meta
        coll = self.child.Meta.model
        result = coll.insert_many(validated_data)
        # attach each new ObjectId back into its dict
        for item, _id in zip(validated_data, result.inserted_ids):
            item['_id'] = _id
        return validated_data


class FileMongoSerializer(serializers.Serializer):
    """
    Serializer for FileCrawl.file dicts, ready to be persisted to MongoDB.
    """

    # ─── Numeric / Scalar fields ──────────────────────────────────────────────
    phone = serializers.IntegerField(required=False, allow_null=True, help_text="Phone number, as an integer (None if unavailable).")
    title = serializers.CharField(max_length=255, help_text="Listing title extracted from the page.")
    metraj = serializers.CharField(max_length=50, required=False, allow_blank=True, help_text="متراژ (area), e.g. '75 متر'.")
    age = serializers.CharField(max_length=50, required=False, allow_blank=True, help_text="سن بنا (age), e.g. '5 سال'.")
    otagh = serializers.CharField(max_length=50, required=False, allow_blank=True, help_text="تعداد اتاق (rooms), e.g. '2'.")
    total_price = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="قیمت کل, e.g. '۳,۰۰۰,۰۰۰,۰۰۰ تومان'.")
    price_per_meter = serializers.CharField(max_length=100, required=False, allow_blank=True, help_text="قیمت هر متر.")
    floor_number = serializers.CharField(max_length=50, required=False, allow_blank=True, help_text="شماره طبقه.")

    # ─── Collections ──────────────────────────────────────────────────────────
    general_features = serializers.ListField(child=serializers.CharField(), required=False, default=list, help_text="List of basic features (e.g. پارکینگ, آسانسور…).")
    features = serializers.ListField(child=serializers.CharField(), required=False, default=list, help_text="Full list of 'امکانات' from the modal.")
    image_srcs = serializers.ListField(child=serializers.URLField(), required=False, default=list, help_text="All image URLs gathered from the gallery.")
    image_paths = serializers.ListField(child=serializers.URLField(), required=False, default=list, help_text="All uploaded image paths gathered from the gallery.")

    # ─── Complex / JSON ───────────────────────────────────────────────────────
    specs = serializers.DictField(child=serializers.CharField(), required=False, default=dict, help_text="Key/value specs from the 'نمایش همهٔ جزئیات' modal.")

    # ─── Free-text / URLs ─────────────────────────────────────────────────────
    description = serializers.CharField(required=False, allow_blank=True, help_text="Cleaned description text.")
    url = serializers.URLField(help_text="Original listing URL.")

    def validate_phone(self, value):
        """
        Ensure phone numbers are positive.
        """
        if value is not None and value < 0:
            raise serializers.ValidationError("Phone number must be positive.")
        return value

    def validate(self, data):
        logger_file.info(f"data.get('image_srcs'): {len(data.get('image_srcs'))}, like: {data.get('image_srcs')[0]}")
        if data.get('image_srcs'):  # upload the image (from url) and return the image path
            image_paths = []
            for url in data.get('image_srcs'):
                path = upload_and_get_image_path(url, get_next_sequence(get_mongo_db(), 'file'))
                if path:
                    image_paths.append(path)
            data['image_paths'] = image_paths

        return data
        if data.get('total_price') and not data.get('price_per_meter'):
            raise serializers.ValidationError({
                'price_per_meter': "This field is required when total_price is set."
            })
        return data

    class Meta:
        # point at your pymongo collection
        mongo_db = get_mongo_db()
        model = mongo_db.file
        # tell DRF to use our bulk‐creator when many=True
        list_serializer_class = CreateListSerializer

    def create(self, validated_data):
        # single‐object insert
        coll = self.Meta.model
        result = coll.insert_one(validated_data)
        validated_data['_id'] = result.inserted_id
        return validated_data