FROM python:3.13-slim

WORKDIR /code

COPY soegemaskine/searchapi/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the entire src directory to maintain module imports
COPY ./ /code/

# Set up non-root user with UID 1000 (same as bookuser for consistency)
RUN groupadd -r searchuser -g 1000 && useradd -r -g searchuser -u 1000 searchuser
RUN chown -R searchuser:searchuser /code
USER searchuser

CMD ["uvicorn", "soegemaskine.searchapi.dhosearch:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
