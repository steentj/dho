FROM python:3.13-slim

WORKDIR /code

COPY soegemaskine/searchapi/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the entire src directory to maintain module imports
COPY ./ /code/

CMD ["uvicorn", "soegemaskine.searchapi.dhosearch:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
