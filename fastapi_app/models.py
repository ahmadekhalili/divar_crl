from pydantic import BaseModel, AnyHttpUrl, Field, validator
from typing import List, Dict, Optional

from datetime import datetime


# ─── mongo fields ────────────────────────
class ApartmentItem(BaseModel):  # 'category' has different db so dont save here as field
    uid: str   # required, id created for each file by divar
    is_ejare: bool
    phone: Optional[int] = Field(None, description="Phone number, None if unavailable")
    title: str = Field("", max_length=255, description="Listing title")  # put ... instead of ... for required
    rough_time: str = Field("", max_length=255, description="time file posted to divar like: نیم ساعت پیش")
    rough_address: str = Field("", max_length=255)
    metraj: Optional[str] = Field("", max_length=50)  # if not provided value, set to blank str and dont raise error
    age: Optional[str] = Field("", max_length=50)
    otagh: Optional[str] = Field("", max_length=50)
    total_price: Optional[str] = Field("", max_length=100)
    price_per_meter: Optional[str] = Field("", max_length=100)
    floor_number: Optional[str] = Field("", max_length=50)

    vadie: Optional[str] = Field("")
    ejare: Optional[str] = Field("")
    vadie_exchange: Optional[str] = Field("")

    zamin_metraj : Optional[str] = Field("")       # only for vali hoses

    general_features: List[str]   = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    features: List[str]   = Field(default_factory=list)
    image_srcs: List[str]   = Field(default_factory=list)
    image_paths: List[str]   = Field(default_factory=list)
    map_paths: List[str]   = Field(default_factory=list)
    map_tiles_urls: List[str] = Field(default_factory=list)
    map_tiles_buildings: Dict[str, List] = Field(default_factory=dict)

    specs: Dict[str, str] = Field(default_factory=dict)
    description: Optional[str] = Field("")
    agency: Optional[str] = Field("")
    url: str

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    expired: bool = False

    @validator("phone")
    def phone_must_be_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("Phone number must be positive")
        return v

    @staticmethod
    async def index_creation(mongo_db):
        await mongo_db.apartment.create_index("uid")  # .create_index("uid", unique=True)
        await mongo_db.zamin_kolangy.create_index("uid")
        await mongo_db.vila.create_index("uid")

        await mongo_db.apartment.create_index("expired")
        await mongo_db.zamin_kolangy.create_index("expired")
        await mongo_db.vila.create_index("expired")

        await mongo_db.apartment.create_index("created")
        await mongo_db.zamin_kolangy.create_index("created")
        await mongo_db.vila.create_index("created")

    @staticmethod
    async def index_deletaion(mongo_db):  # for apply new indexes without error
        await mongo_db.apartment.drop_index("uid_1")  # .create_index("uid", unique=True)
        await mongo_db.zamin_kolangy.drop_index("uid_1")
        await mongo_db.vila.drop_index("uid_1")

        await mongo_db.apartment.drop_index("expired_1")
        await mongo_db.zamin_kolangy.drop_index("expired_1")
        await mongo_db.vila.drop_index("expired_1")

        await mongo_db.apartment.drop_index("created_1")
        await mongo_db.zamin_kolangy.drop_index("created_1")
        await mongo_db.vila.drop_index("created_1")
