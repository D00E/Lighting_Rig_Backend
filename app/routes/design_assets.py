from fastapi import APIRouter, HTTPException
from psycopg import Error
from psycopg.rows import dict_row

from app.db import get_connection
from app.schemas.design_asset import DesignAssetCreate, DesignAssetOut


router = APIRouter(prefix="/design-assets", tags=["design-assets"])


@router.post("", response_model=DesignAssetOut)
def create_design_asset(payload: DesignAssetCreate) -> dict:
    query = """
        INSERT INTO design_assets (
            design_id,
            asset_type,
            storage_bucket,
            storage_path,
            content_type,
            size_bytes
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING
            id,
            design_id,
            asset_type,
            storage_bucket,
            storage_path,
            content_type,
            size_bytes,
            created_at;
    """

    values = (
        str(payload.design_id),
        payload.asset_type,
        payload.storage_bucket,
        payload.storage_path,
        payload.content_type,
        payload.size_bytes,
    )

    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, values)
                created = cursor.fetchone()
            connection.commit()
    except Error as error:
        message = str(error).strip()
        raise HTTPException(status_code=400, detail=f"Failed to insert design asset: {message}") from error

    if created is None:
        raise HTTPException(status_code=400, detail="Failed to insert design asset")

    return created
