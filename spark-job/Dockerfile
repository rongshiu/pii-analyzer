# Use Spark image with PySpark
FROM apache/spark-py:v3.4.0

USER root

# Install OS dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    lsb-release \
    apt-transport-https \
    ca-certificates \
    gnupg \
    libpq-dev \
    tesseract-ocr \
    poppler-utils \
    dirmngr && \
    apt-get clean

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Internal shared package from a private repo (not publicly available)
RUN --mount=type=secret,id=github_token \
    pip install \
    "git+https://$(cat /run/secrets/github_token)@github.com/ORG/INTERNAL-SHARED-PACKAGE.git@main#subdirectory=pkg/python"

# Copy source code
COPY app/ /app/
WORKDIR /app

ARG VERSION=dev
ARG COMMIT=none
ARG BUILD_TIME=unknown

RUN sed -i "s/__version__ = .*/__version__ = \"$VERSION\"/" ./utility/version.py && \
    sed -i "s/__commit__ = .*/__commit__ = \"$COMMIT\"/" ./utility/version.py && \
    sed -i "s/__build_time__ = .*/__build_time__ = \"$BUILD_TIME\"/" ./utility/version.py 

# Download Hadoop AWS and PostgreSQL JDBC connector
ENV HADOOP_VERSION=3.3.4
ENV AWS_JAR_URL=https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/$HADOOP_VERSION/hadoop-aws-$HADOOP_VERSION.jar
ENV AWS_SDK_BUNDLE_URL=https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.11.1026/aws-java-sdk-bundle-1.11.1026.jar
ENV POSTGRES_JDBC_URL=https://jdbc.postgresql.org/download/postgresql-42.7.3.jar

# Create directory for jars and download them
RUN mkdir -p /opt/spark/jars && \
    wget -q $AWS_JAR_URL -P /opt/spark/jars && \
    wget -q $AWS_SDK_BUNDLE_URL -P /opt/spark/jars && \
    wget -q $POSTGRES_JDBC_URL -P /opt/spark/jars

# Set SPARK_JARS_DIR
ENV SPARK_EXTRA_CLASSPATH="/opt/spark/jars/*" \
    PYTHONPATH="/app:$PYTHONPATH"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]