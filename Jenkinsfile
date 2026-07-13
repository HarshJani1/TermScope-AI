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
                '''
            }
        }

        stage('Stop Running Services') {
            steps {
                sh '''
                    echo "Stopping any running TermScope docker containers ..."
                    docker rm -f termscope-backend || true
                    docker rm -f termscope-frontend || true
                '''
            }
        }

        stage('Deploy Backend') {
            steps {
                sh '''
                    echo "Deploying backend ..."

                    # Copy backend source to deploy directory
                    rsync -a --delete \
                        --exclude='.venv' \
                        --exclude='__pycache__' \
                        --exclude='.pytest_cache' \
                        --exclude='.env' \
                        "$WORKSPACE/backend/" "$DEPLOY_DIR/backend/"

                    echo "Backend source deployed to $DEPLOY_DIR/backend"
                '''
            }
        }

        stage('Setup Database') {
            steps {
                sh '''
                    echo "Creating MySQL database if not exists using docker container..."
                    docker run --rm \
                        --network host \
                        -v "$DEPLOY_DIR/backend:/workspace/backend" \
                        -w /workspace/backend \
                        -e DB_HOST=localhost \
                        -e DB_USER="$DB_USER" \
                        -e DB_PASSWORD="$DB_PASSWORD" \
                        -e DB_NAME="$DB_NAME" \
                        "$CI_IMAGE" \
                        python create_db.py
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
                withCredentials([
                    string(credentialsId: 'groq-api-key', variable: 'GROQ_API_KEY')
                ]) {
                    sh '''
                        echo "Starting TermScope services inside Docker containers ..."

                        # ── Start Backend Container ──
                        docker run -d \
                            --name termscope-backend \
                            --network host \
                            --restart unless-stopped \
                            -v "$DEPLOY_DIR/backend:/workspace/backend" \
                            -w /workspace/backend \
                            -e FLASK_ENV=production \
                            -e DB_HOST=localhost \
                            -e DB_USER="$DB_USER" \
                            -e DB_PASSWORD="$DB_PASSWORD" \
                            -e DB_NAME="$DB_NAME" \
                            -e GROQ_API_KEY="$GROQ_API_KEY" \
                            -e SECRET_KEY="$(openssl rand -hex 32)" \
                            -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
                            -e JWT_EXPIRY_HOURS=24 \
                            -e MAX_FILE_SIZE_MB=16 \
                            -e EMBEDDING_MODEL=all-MiniLM-L6-v2 \
                            -e CHUNK_SIZE=1000 \
                            -e CHUNK_OVERLAP=200 \
                            -e REDIS_HOST=localhost \
                            -e REDIS_PORT=6379 \
                            -e REDIS_URL=redis://localhost:6379/0 \
                            -e RATE_LIMIT_CAPACITY=10 \
                            -e RATE_LIMIT_REFILL_RATE=1.0 \
                            "$CI_IMAGE" \
                            python app.py

                        # ── Start Frontend Container ──
                        docker run -d \
                            --name termscope-frontend \
                            --network host \
                            --restart unless-stopped \
                            -v "$DEPLOY_DIR/frontend:/workspace/frontend" \
                            -w /workspace/frontend \
                            "$CI_IMAGE" \
                            python3 -m http.server 5173

                        # Wait for processes to stabilise
                        sleep 5

                        # Verify containers are running
                        echo "── Process Status ──"
                        docker ps --filter "name=termscope-"
                    '''
                }
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
                        echo "── Backend Container Logs ──"
                        docker logs termscope-backend || true
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

