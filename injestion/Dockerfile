FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY gym_scraper.py ${LAMBDA_TASK_ROOT}/

CMD ["gym_scraper.lambda_handler"]
