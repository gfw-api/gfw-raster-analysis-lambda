import json
import boto3
import logging
import os
import requests
from datetime import datetime, date, timedelta

from raster_analysis.exceptions import (
    GeostoreNotFoundException,
    RasterAnalysisException,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

RASTER_ANALYSIS_LAMBDA_NAME = os.environ["RASTER_ANALYSIS_LAMBDA_NAME"]
TILED_ANALYSIS_LAMBDA_NAME = os.environ["TILED_ANALYSIS_LAMBDA_NAME"]

if "ENV" in os.environ:
    ENV = os.environ["ENV"]
else:
    ENV = "dev"

GFW_API_URI = f"https://{'production' if ENV == 'production' else 'staging'}-api.globalforestwatch.org"
GLAD_UNCONFIRMED_CONST = 20000
GLAD_CONFIRMED_CONST = 30000


# TODO add lambda validate decorator
def handler(event, context):
    query_params = event["queryStringParameters"]
    multi_val_query_params = event["multiValueQueryStringParameters"]
    path = event["path"]

    geom_id = query_params["geostore_id"]
    del query_params["geostore_id"]

    try:
        geom, area_ha = get_geostore(geom_id)
    except GeostoreNotFoundException:
        return {
            "isBase64Encoded": False,
            "statusCode": 404,
            "body": f"Geostore {geom_id} not found",
        }

    payload = get_raster_analysis_payload(
        geom, query_params, multi_val_query_params, path
    )
    logger.info("Running raster analysis with params: " + json.dumps(payload))

    try:
        result = run_raster_analysis(payload, area_ha)
        csv_result = convert_to_csv_json_style(result)

        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(csv_result),
        }
    except RasterAnalysisException:
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "headers": {"Content-Type": "text/plain"},
            "body": f"Internal Server Error <{context.aws_request_id}>",
        }


def get_raster_analysis_payload(geom, query_params, multi_val_query_params, path):
    payload = dict()

    payload["geometry"] = geom
    payload.update(query_params)

    for key, val_list in multi_val_query_params.items():
        if len(val_list) > 1:
            payload[
                key
            ] = val_list  # override single value params if they have multiple values

    if path == "/analysis/treecoverloss":
        update_treecoverloss_payload(payload)
    elif path == "/analysis/gladalerts":
        update_gladalerts_payload(payload)
    else:
        payload["analyses"] = ["area"]

    if "threshold" in payload:
        payload["threshold"] = int(
            payload["threshold"]
        )  # number query params are all passed in as strings

    if "extent_year" in payload:
        payload["extent_year"] = int(payload["extent_year"])
    else:
        payload["extent_year"] = 2000

    return payload


def update_treecoverloss_payload(payload):
    payload["analysis_raster_id"] = "loss"

    if "start" in payload:
        payload["start"] = int(payload["start"][2:])
    if "end" in payload:
        payload["end"] = int(payload["end"][2:])

    payload["analyses"] = ["area"]


def update_gladalerts_payload(payload):
    payload["analysis_raster_id"] = "glad_alerts"

    if "start" in payload:
        payload["start"] = get_gladalerts_date(payload["start"])
    if "end" in payload:
        payload["end"] = get_gladalerts_date(payload["end"])

    payload["analyses"] = ["count"]


def get_gladalerts_date(date_str):
    raw_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    days_since_2015 = (raw_date - date(2015, 1, 1)).days
    return days_since_2015 + GLAD_CONFIRMED_CONST


def run_raster_analysis(payload, area_ha):
    lambda_client = boto3.client("lambda")

    if area_ha < 5000000:
        lambda_response = lambda_client.invoke(
            FunctionName=RASTER_ANALYSIS_LAMBDA_NAME,
            InvocationType="RequestResponse",
            Payload=bytes(json.dumps(payload), "utf-8"),
        )
    else:
        lambda_response = lambda_client.invoke(
            FunctionName=TILED_ANALYSIS_LAMBDA_NAME,
            InvocationType="RequestResponse",
            Payload=bytes(json.dumps(payload), "utf-8"),
        )

    response = json.loads(lambda_response["Payload"].read())

    if response["statusCode"] != 200:
        logger.error(f"Raster analysis returned status code f{response['statusCode']})")
        raise RasterAnalysisException()

    body = json.loads(response["body"])
    return body


def get_geostore(geom_id):
    response = requests.get(f"{GFW_API_URI}/geostore/{geom_id}")

    if response.status_code == 404:
        raise GeostoreNotFoundException(
            f"Geometry wih ID = {geom_id} not found in GeoStore."
        )

    body = response.json()

    # Right now, just the first geometry
    geom = body["data"]["attributes"]["geojson"]["features"][0]["geometry"]
    areaHa = body["data"]["attributes"]["areaHa"]

    return geom, areaHa


def convert_to_csv_json_style(results):
    result_cols = list(results.keys())
    result_row_length = len(results[result_cols[0]])
    rows = []

    for i in range(0, result_row_length):
        row = dict()
        for col in result_cols:
            if col == "loss":
                row["loss__year"] = results[col][i] + 2000
            elif col == "glad_alerts":
                days_since_2015 = results[col][i] - GLAD_CONFIRMED_CONST
                raw_date = date(2015, 1, 1) + timedelta(days=days_since_2015)
                row["alert__date"] = raw_date.strftime("%Y-%m-%d")
            else:
                row[col] = results[col][i]

        rows.append(row)

    return rows
