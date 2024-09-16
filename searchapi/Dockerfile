FROM python:3.12

WORKDIR /code

COPY ./requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./ /code/searchapi

CMD ["uvicorn", "searchapi.dhosearch:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
