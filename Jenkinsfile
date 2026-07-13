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
        DEPLOY_DIR = "${HOME}/TermScope"
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
                    mkdir -p "$DEPLOY_DIR/backend"
                    mkdir -p "$DEPLOY_DIR/frontend"
                    mkdir -p "$DEPLOY_DIR/pids"
                    mkdir -p "$DEPLOY_DIR/logs"
                '''
            }
        }

        stage('Stop Running Services') {
            steps {
                sh '''
                    echo "Stopping any running TermScope services ..."

                    # Stop backend if running
                    if [ -f "$DEPLOY_DIR/pids/backend.pid" ]; then
                        PID=$(cat "$DEPLOY_DIR/pids/backend.pid")
                        if kill -0 "$PID" 2>/dev/null; then
                            echo "Stopping backend (PID $PID) ..."
                            kill "$PID" || true
                            sleep 2
                            # Force kill if still running
                            kill -0 "$PID" 2>/dev/null && kill -9 "$PID" || true
                        fi
                        rm -f "$DEPLOY_DIR/pids/backend.pid"
                    fi

                    # Stop frontend if running
                    if [ -f "$DEPLOY_DIR/pids/frontend.pid" ]; then
                        PID=$(cat "$DEPLOY_DIR/pids/frontend.pid")
                        if kill -0 "$PID" 2>/dev/null; then
                            echo "Stopping frontend (PID $PID) ..."
                            kill "$PID" || true
                            sleep 2
                            kill -0 "$PID" 2>/dev/null && kill -9 "$PID" || true
                        fi
                        rm -f "$DEPLOY_DIR/pids/frontend.pid"
                    fi

                    echo "Services stopped."
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

        stage('Start Services') {
            steps {
                sh '''
                    echo "Starting TermScope services ..."

                    # ── Start Backend ──
                    cd "$DEPLOY_DIR/backend"
                    nohup "$DEPLOY_DIR/backend/.venv/bin/python" app.py \
                        > "$DEPLOY_DIR/logs/backend.log" 2>&1 &
                    echo $! > "$DEPLOY_DIR/pids/backend.pid"
                    echo "Backend started (PID $(cat "$DEPLOY_DIR/pids/backend.pid"))"

                    # ── Start Frontend ──
                    cd "$DEPLOY_DIR/frontend"
                    nohup python3 -m http.server 5173 \
                        > "$DEPLOY_DIR/logs/frontend.log" 2>&1 &
                    echo $! > "$DEPLOY_DIR/pids/frontend.pid"
                    echo "Frontend started (PID $(cat "$DEPLOY_DIR/pids/frontend.pid"))"

                    # Wait for processes to stabilise
                    sleep 5

                    # Verify processes are running
                    echo "── Process Status ──"
                    BACKEND_PID=$(cat "$DEPLOY_DIR/pids/backend.pid")
                    FRONTEND_PID=$(cat "$DEPLOY_DIR/pids/frontend.pid")

                    if kill -0 "$BACKEND_PID" 2>/dev/null; then
                        echo "Backend  : RUNNING (PID $BACKEND_PID)"
                    else
                        echo "Backend  : FAILED — check $DEPLOY_DIR/logs/backend.log"
                        cat "$DEPLOY_DIR/logs/backend.log"
                        exit 1
                    fi

                    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
                        echo "Frontend : RUNNING (PID $FRONTEND_PID)"
                    else
                        echo "Frontend : FAILED — check $DEPLOY_DIR/logs/frontend.log"
                        cat "$DEPLOY_DIR/logs/frontend.log"
                        exit 1
                    fi
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
                        echo "── Backend Log ──"
                        cat "$DEPLOY_DIR/logs/backend.log" || true
                        exit 1
                    fi

                    echo ""
                    echo "==========================================="
                    echo "  Deployment completed successfully!"
                    echo "  Backend  → http://localhost:5010"
                    echo "  Frontend → http://localhost:5173"
                    echo "==========================================="
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

