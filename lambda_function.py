import logging
import sys

from lambda_decorators import json_http_resp, json_schema_validator
from shapely.geometry import shape

from raster_analysis import geoprocessing
from raster_analysis.geoprocessing import Filter
from raster_analysis.schemas import SCHEMA

BASE_URL = "/vsis3/gfw-files/2018_update/{raster_id}/{tile_id}.tif"

fmt = "%(asctime)s %(levelname)-4s - %(name)s - %(message)s"
datefmt = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=fmt)
logger = logging.getLogger(__name__)


@json_schema_validator(request_schema=SCHEMA)
@json_http_resp
def lambda_handler(event, context):

    logger.info("Test")
    analysis_raster_id = event["analysis_raster_id"]
    contextual_raster_ids = (
        event["contextual_raster_ids"] if "contextual_raster_ids" in event else []
    )
    aggregate_raster_ids = (
        event["aggregate_raster_ids"] if "aggregate_raster_ids" in event else []
    )
    analyses = event["analyses"] if "analyses" in event else ["count", "area"]
    geometry = shape(event["geometry"])

    filters = [Filter(**f) for f in event["filters"]] if "filters" in event else []

    return geoprocessing.analysis(
        geometry,
        analysis_raster_id,
        contextual_raster_ids,
        aggregate_raster_ids,
        filters,
        analyses,
    )


if __name__ == "__main__":
    # "{\"analysis_raster_id\":\"loss\", \"contextual_raster_ids\":[\"wdpa\"], \"aggregate_raster_ids\":[\"tcd_2000\", \"tcd_2010\"], \"analysis\":\"sum\", \"geometry\":{\"type\":\"Polygon\",\"coordinates\":[[[9.0,4.1],[9.1,4.1],[9.1,4.2],[9.0,4.2],[9.0,4.1]]]},\"filters\":[{\"raster_id\":\"tcd_2000\",\"threshold\":30}]}"), None))
    print(
        lambda_handler(
            {
                "analysis_raster_id": "loss",
                "contextual_raster_ids": ["wdpa"],
                "analyses": ["count", "area"],
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[9, 4.1], [9.1, 4.1], [9.1, 4.2], [9, 4.2], [9, 4.1]]
                    ],
                },
                "filters": [{"raster_id": "tcd_2000", "threshold": 30}],
            },
            None,
        )
    )
