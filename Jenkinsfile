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
    }

    post {
        success {
            archiveArtifacts artifacts: 'frontend/dist/**', fingerprint: true
        }
    }
}
