from setuptools import setup

setup(
    name="gfw_raster-analysis-lambda",
    version="0.2.0",
    description="Lambda function to run serverless on the fly raster analysis",
    packages=["raster_analysis"],
    author="Thomas Maschler",
    license="MIT",
    install_requires=[
        "rasterio[s3]~=1.0.28",
        "shapely~=1.6.4.post2",
        "pyproj~=2.1.3",
        "pandas~=0.25.1",
        "lambda-decorators~=0.3.0",
        "aws-xray-sdk",
    ],
)
