from fastapi import APIRouter, HTTPException
from psycopg import Error
from psycopg.rows import dict_row

from app.db import get_connection
from app.schemas.design import DesignCreate, DesignOut


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


@router.get("", response_model=list[DesignOut])
def list_designs() -> list[dict]:
    query = """
        SELECT
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
            updated_at
        FROM designs
        ORDER BY created_at DESC;
    """

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    return rows
