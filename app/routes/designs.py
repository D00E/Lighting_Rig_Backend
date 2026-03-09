from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Response
from psycopg import Error
from psycopg.rows import dict_row

from app.db import get_connection
from app.schemas.design import DesignCreate, DesignOut, DesignWithPreviewOut
from app.services.storage import download_bytes


router = APIRouter(prefix="/designs", tags=["designs"])


@router.post("", response_model=DesignOut)
def create_design(payload: DesignCreate) -> dict:
    query = """
        INSERT INTO designs (
            callsign,
            design_type,
            gif_name,
            creator,
            description,
            num_frames,
            num_packets
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING
            id,
            callsign,
            design_type,
            gif_name,
            creator,
            description,
            num_frames,
            num_packets,
            download_count,
            created_at,
            updated_at;
    """

    values = (
        payload.callsign,
        payload.design_type,
        payload.gif_name,
        payload.creator,
        payload.description,
        payload.num_frames,
        payload.num_packets,
    )

    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(query, values)
                created = cursor.fetchone()
            connection.commit()
    except Error as error:
        message = str(error).strip()
        raise HTTPException(status_code=400, detail=f"Failed to insert design: {message}") from error

    if created is None:
        raise HTTPException(status_code=400, detail="Failed to insert design")

    return created


@router.get("", response_model=list[DesignWithPreviewOut])
def list_designs() -> list[dict]:
    query = """
        SELECT
            d.id,
            d.callsign,
            d.design_type,
            d.gif_name,
            d.creator,
            d.description,
            d.num_frames,
            d.num_packets,
            d.download_count,
            d.created_at,
            d.updated_at,
            da.storage_bucket AS preview_storage_bucket,
            da.storage_path AS preview_storage_path,
            da.content_type AS preview_content_type
        FROM designs d
        LEFT JOIN design_assets da
            ON da.design_id = d.id
           AND da.asset_type = 'preview_gif'
        ORDER BY d.created_at DESC;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    return rows


@router.get("/{design_id}", response_model=DesignWithPreviewOut)
def get_design(design_id: UUID) -> dict:
    query = """
        SELECT
            d.id,
            d.callsign,
            d.design_type,
            d.gif_name,
            d.creator,
            d.description,
            d.num_frames,
            d.num_packets,
            d.download_count,
            d.created_at,
            d.updated_at,
            da.storage_bucket AS preview_storage_bucket,
            da.storage_path AS preview_storage_path,
            da.content_type AS preview_content_type
        FROM designs d
        LEFT JOIN design_assets da
            ON da.design_id = d.id
           AND da.asset_type = 'preview_gif'
        WHERE d.id = %s
        LIMIT 1;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (str(design_id),))
            row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Design not found")

    return row


@router.get("/{callsign}/payload", response_class=Response)
def get_payload(callsign: str = Path(..., min_length=6, max_length=6)) -> Response:
    query = """
        SELECT
            da.storage_bucket,
            da.storage_path,
            da.content_type
        FROM designs d
        JOIN design_assets da ON da.design_id = d.id
        WHERE d.callsign = %s
          AND da.asset_type = 'encoded_payload'
        LIMIT 1;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, (callsign,))
            row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Payload asset not found")

    try:
        payload_bytes, _ = download_bytes(row["storage_bucket"], row["storage_path"])
    except RuntimeError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return Response(content=payload_bytes, media_type="text/plain")
