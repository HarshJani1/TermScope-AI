pipeline {
    agent any

    environment {
        FLASK_ENV = 'testing'
        PYTHONUNBUFFERED = '1'
        CI_IMAGE = 'harsh1jani/termscope-ci-common:latest'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Pull CI Image') {
            steps {
                sh 'docker pull "$CI_IMAGE"'
            }
        }

        stage('Backend Tests') {
            steps {
                sh '''
                    docker run --rm \
                        -e FLASK_ENV="$FLASK_ENV" \
                        -e PYTHONUNBUFFERED="$PYTHONUNBUFFERED" \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace/backend \
                        "$CI_IMAGE" \
                        sh -lc 'pytest'
                '''
            }
        }

        stage('Frontend Lint') {
            steps {
                sh '''
                    docker run --rm \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace/frontend \
                        "$CI_IMAGE" \
                        sh -lc 'npm run lint'
                '''
            }
        }

        stage('Frontend Build') {
            steps {
                sh '''
                    docker run --rm \
                        -v "$WORKSPACE:/workspace" \
                        -w /workspace/frontend \
                        "$CI_IMAGE" \
                        sh -lc 'npm run build'
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
