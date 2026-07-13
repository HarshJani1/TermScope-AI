pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timestamps()
    }

    environment {
        FLASK_ENV = 'testing'
        PYTHONUNBUFFERED = '1'
        CI_IMAGE = 'harsh1jani/termscope-ci-common:latest'
        CI_PLATFORM = 'linux/amd64'
        DEPLOY_DIR = '/opt/TermScope'
        DB_USER = 'root'
        DB_PASSWORD = 'Password'
        DB_NAME = 'termscope'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Docker Preflight') {
            steps {
                sh 'docker info'
            }
        }

        stage('Pull CI Image') {
            steps {
                sh 'docker pull --platform "$CI_PLATFORM" "$CI_IMAGE"'
            }
        }

        stage('Backend Tests') {
            steps {
                withCredentials([
                    string(credentialsId: 'groq-api-key', variable: 'GROQ_API_KEY')
                ]) {
                    sh '''
                        docker run --rm \
                            --platform "$CI_PLATFORM" \
                            -e FLASK_ENV="$FLASK_ENV" \
                            -e PYTHONUNBUFFERED="$PYTHONUNBUFFERED" \
                            -e GROQ_API_KEY="$GROQ_API_KEY" \
                            -v "$WORKSPACE:/workspace" \
                            -w /workspace/backend \
                            "$CI_IMAGE" \
                            sh -lc 'pytest'
                    '''
                }
            }
        }

        stage('Frontend Lint') {
            steps {
                sh '''
                    docker run --rm \
                        --platform "$CI_PLATFORM" \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace/frontend \
                        "$CI_IMAGE" \
                        sh -lc 'npm ci && npm run lint'
                '''
            }
        }

        stage('Frontend Build') {
            steps {
                sh '''
                    docker run --rm \
                        --platform "$CI_PLATFORM" \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace/frontend \
                        "$CI_IMAGE" \
                        sh -lc 'npm ci && npm run build'
                '''
            }
        }

        // ──────────────────────────────────────────────
        //  CONTINUOUS DEPLOYMENT STAGES
        // ──────────────────────────────────────────────

        stage('Prepare Deploy Directory') {
            steps {
                sh '''
                    echo "Creating deployment directory at $DEPLOY_DIR ..."
                    sudo mkdir -p "$DEPLOY_DIR/backend"
                    sudo mkdir -p "$DEPLOY_DIR/frontend"
                    sudo chown -R $(whoami):$(whoami) "$DEPLOY_DIR"
                '''
            }
        }

        stage('Deploy Backend') {
            steps {
                withCredentials([
                    string(credentialsId: 'groq-api-key', variable: 'GROQ_API_KEY')
                ]) {
                    sh '''
                        echo "Deploying backend ..."

                        # Copy backend source to deploy directory
                        rsync -a --delete \
                            --exclude='.venv' \
                            --exclude='__pycache__' \
                            --exclude='.pytest_cache' \
                            --exclude='.env' \
                            "$WORKSPACE/backend/" "$DEPLOY_DIR/backend/"

                        # Create Python virtual environment if it does not exist
                        if [ ! -d "$DEPLOY_DIR/backend/.venv" ]; then
                            echo "Creating Python virtual environment ..."
                            python3 -m venv "$DEPLOY_DIR/backend/.venv"
                        fi

                        # Install / update dependencies
                        echo "Installing backend dependencies ..."
                        . "$DEPLOY_DIR/backend/.venv/bin/activate"
                        pip install --upgrade pip -q
                        pip install torch --index-url https://download.pytorch.org/whl/cpu -q
                        pip install -r "$DEPLOY_DIR/backend/requirements.txt" -q
                        deactivate

                        # Write production .env file
                        cat > "$DEPLOY_DIR/backend/.env" <<EOF
# TermScope Production Environment — managed by Jenkins
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# MySQL
DB_HOST=localhost
DB_PORT=3306
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_NAME=$DB_NAME

# JWT
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_EXPIRY_HOURS=24

# Groq LLM
GROQ_API_KEY=$GROQ_API_KEY
LLM_MODEL=openai/gpt-oss-120b
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.3

# File Upload
MAX_FILE_SIZE_MB=16

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Text Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379/0

# Rate Limiting
RATE_LIMIT_CAPACITY=10
RATE_LIMIT_REFILL_RATE=1.0
EOF

                        echo "Backend deployed to $DEPLOY_DIR/backend"
                    '''
                }
            }
        }

        stage('Setup Database') {
            steps {
                sh '''
                    echo "Creating MySQL database if not exists ..."
                    mysql -u "$DB_USER" -p"$DB_PASSWORD" -e \
                        "CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                    echo "Database '$DB_NAME' is ready."
                '''
            }
        }

        stage('Deploy Frontend') {
            steps {
                sh '''
                    echo "Deploying frontend build ..."
                    rsync -a --delete \
                        "$WORKSPACE/frontend/dist/" "$DEPLOY_DIR/frontend/"
                    echo "Frontend deployed to $DEPLOY_DIR/frontend"
                '''
            }
        }

        stage('Create Systemd Services') {
            steps {
                sh '''
                    echo "Setting up systemd service for backend ..."

                    # ── Backend service ──
                    sudo tee /etc/systemd/system/termscope-backend.service > /dev/null <<EOF
[Unit]
Description=TermScope Flask Backend
After=network.target mysql.service redis.service

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$DEPLOY_DIR/backend
EnvironmentFile=$DEPLOY_DIR/backend/.env
ExecStart=$DEPLOY_DIR/backend/.venv/bin/python app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

                    # ── Frontend static file server ──
                    sudo tee /etc/systemd/system/termscope-frontend.service > /dev/null <<EOF
[Unit]
Description=TermScope Frontend (static file server)
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$DEPLOY_DIR/frontend
ExecStart=/usr/bin/python3 -m http.server 5173
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

                    sudo systemctl daemon-reload
                    echo "Systemd services created."
                '''
            }
        }

        stage('Start Services') {
            steps {
                sh '''
                    echo "Starting TermScope services ..."

                    # Restart (or start) backend
                    sudo systemctl enable termscope-backend.service
                    sudo systemctl restart termscope-backend.service

                    # Restart (or start) frontend
                    sudo systemctl enable termscope-frontend.service
                    sudo systemctl restart termscope-frontend.service

                    # Wait a few seconds for processes to stabilise
                    sleep 5

                    echo "── Service Status ──"
                    sudo systemctl status termscope-backend.service --no-pager || true
                    sudo systemctl status termscope-frontend.service --no-pager || true
                '''
            }
        }

        stage('Health Check') {
            steps {
                sh '''
                    echo "Running health check ..."
                    for i in 1 2 3 4 5; do
                        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5010/api/health || true)
                        if [ "$HTTP_CODE" = "200" ]; then
                            echo "Backend health check PASSED (HTTP $HTTP_CODE)"
                            break
                        fi
                        echo "Attempt $i: HTTP $HTTP_CODE — retrying in 3s ..."
                        sleep 3
                    done

                    if [ "$HTTP_CODE" != "200" ]; then
                        echo "ERROR: Backend health check FAILED after 5 attempts"
                        exit 1
                    fi

                    echo "Deployment completed successfully!"
                    echo "  Backend  → http://localhost:5010"
                    echo "  Frontend → http://localhost:5173"
                '''
            }
        }
    }

    post {
        success {
            archiveArtifacts artifacts: 'frontend/dist/**', fingerprint: true
            echo 'CI/CD pipeline completed successfully — TermScope is live!'
        }
        failure {
            echo 'Pipeline failed. Check logs above for details.'
        }
    }
}
