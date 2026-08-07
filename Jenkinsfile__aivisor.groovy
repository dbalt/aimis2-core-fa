@Library('DPMPipelineUtils@1.5')
@Library('ru.sbrf.devsecops@master') _

pipeline {
    agent {
        node {
            label 'rhel8&&clearAgent'
        }
    }
    
    environment {
        // app info
    	appComponent = 'aimis2_aivisor'
        appImg = 'aimisAivisorImg'
		repo = 'aimis2-core-fa'
		vers = '01.000.01'
        SONAR_PROJECT_KEY = 'aimis2-core-fa'

        // const
        //project info
        PROJECT = 'AIMIS'

        // const
        // branches
        master_branch = 'master'
        develop_branch = 'develop'

        // const
        // tuz
        tuz_ci = 'cab-sa-dvo09234_AD'
        sberosc_ci = 'sberosc_ci'

        // const
        // as info
        as_code = '02877809'
        fp_code = '08409038'

        // const
        // urls
        docker_url = 'docker-dev.registry-ci.delta.sbrf.ru'
        bitbucket_url = 'https://stash.delta.sbrf.ru'

        // const
        // sonar
        SONAR_HOST_URL = 'https://sonar.delta.sbrf.ru/'
        SONAR_LOGIN = 'cefda292-7575-47d2-bc9a-1022d242f8d0'

        // const
        // tools
        py312 = tool name: 'python3.12', type: 'com.cloudbees.jenkins.plugins.customtools.CustomTool'
        scannerHome = tool 'SonarQube Scanner 3.0.3.778'
    }

    options {
        timestamps()
        timeout(time: 1, unit: 'HOURS')
        buildDiscarder(logRotator(artifactDaysToKeepStr: '7', artifactNumToKeepStr: '10', daysToKeepStr: '7', numToKeepStr: '50'))
    }

    stages {        
        stage('Application Security') {
            when {
                anyOf {
                    branch master_branch 
                }
            }
            steps {
                script {
                    echo "###### Run application security ######"

                    def config = readYaml(file: './devsecops-config.yml')
                    def res = runAppSec(config, "${bitbucket_url}/scm/${PROJECT.toLowerCase()}/${repo}.git", env.GIT_BRANCH, env.GIT_COMMIT)
                    sh "echo ${res}"

                    echo "###### Stage Application Security SUCCESS ######"
                }
            }
        }

        stage('Add SDK') {
            when {
                anyOf {
                    branch master_branch
                    branch develop_branch
                }
            }
            steps {
                script {
                    echo "###### Install AIMIS SDK ######"

                    withCredentials([usernamePassword(
                        credentialsId: tuz_ci,
                        usernameVariable: 'USERNAME',
                        passwordVariable: 'PASSWORD'
                    )]) {
                        sh """
                            git clone https://\${USERNAME}:\${PASSWORD}@stash.delta.sbrf.ru/scm/aimis/aimis-sdk.git
                            mv aimis-sdk/sdk src/
                            rm -rf aimis-sdk
                        """
                    }

                    echo "###### AIMIS SDK successfully installed ######"
                }
            }
        }

        stage('Unit Tests') {
            when {
                anyOf {
                    branch master_branch 
                }
            }
            steps {
                script {
                    echo "###### Run Unit Tests ######"

                    withCredentials([string(credentialsId: "${sberosc_ci}", variable: 'TOKEN')]) {
                        sh """
                            ${py312}/virtualenv -p python3 venv
                            source venv/bin/activate
                            python3 -m pip install coverage==7.10.6 pytest pytest-cov fastapi uvicorn httpx==0.27.2 --index-url=https://token:${TOKEN}@sberosc.sigma.sbrf.ru/repo/pypi/simple --trusted-host=sberosc.sigma.sbrf.ru
                            python3 -m pytest -o junit_family=xunit1 --cov-report xml:coverage.xml --cov=. --junitxml=result.xml tests/
                            deactivate
                        """
                    }

                    echo "###### Stage Unit Tests SUCCESS ######"
                }
            }
        }

        stage('SonarQube Analysis') {
            when {
                anyOf {
                    branch master_branch 
                }
            }
            steps {
                echo "###### Start SonarQube analysis ######"

                withSonarQubeEnv(credentialsId: "${SONAR_LOGIN}", installationName: 'SonarQubeDelta') {                    
                    sh """
                        ${scannerHome}/bin/sonar-scanner \\
                            -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
                            -Dsonar.branch.name=${env.BRANCH_NAME} \
                            -Dsonar.working.directory=/tmp/target/sonar \
                            -Dsonar.sources=src \
                            -Dsonar.python.coverage.reportPaths=coverage.xml
                    """
                }

                echo "###### Stage SonarQube Analysis SUCCESS ######"
            }
        }

        stage('Docker Build') {
            when {
                anyOf {
                    branch master_branch
                    branch develop_branch
                }
            }
            steps {
                script {
                    echo "###### Docker build for ${appComponent} ######"

                    def tagSuffix = ""
                    if (env.BRANCH_NAME == develop_branch) { tagSuffix = "-SNAPSHOT" }

                    withCredentials([string(credentialsId: "${sberosc_ci}", variable: 'TOKEN')]) {
                        withDockerRegistry([credentialsId: "${tuz_ci}", url: "https://${docker_url}/ci${as_code}/ci${fp_code}/"]) {
                            sh "docker build -t ${docker_url}/ci${as_code}/ci${fp_code}/${appComponent}:D-${vers}_${appComponent}${BUILD_ID}${tagSuffix} --build-arg TOKEN=${TOKEN} -f Dockerfile__${appComponent} --label \"GIT_COMMIT=${env.GIT_COMMIT}\" ."
                        }
                    }

                    echo "###### Stage Docker Build SUCCESS ######"
                }
            }
        }

        stage('Docker Push') {
            when {
                anyOf {
                    branch master_branch
                    branch develop_branch
                }
            }
            steps {
                script {
                    echo "###### Push ${appComponent} docker image to registry SNAPSHOT ######"

                    def tagSuffix = ""
                    if (env.BRANCH_NAME == develop_branch) { tagSuffix = "-SNAPSHOT" }

                    withDockerRegistry([credentialsId: "${tuz_ci}", url: "https://${docker_url}/ci${as_code}/ci${fp_code}/"]) {
                        sh "docker push ${docker_url}/ci${as_code}/ci${fp_code}/${appComponent}:D-${vers}_${appComponent}${BUILD_ID}${tagSuffix}"
                    }

                    echo "###### Stage Docker Push SUCCESS ######"
                }
            }
        }

        stage('Distributive name (SHA256)') {
            when {
                anyOf {
                    branch master_branch
                    branch develop_branch
                }
            }
            steps {
                script {
                    echo "###### Get distributive name (sha256) for ${appComponent} image ######"

                    def tagSuffix = ""
                    if (env.BRANCH_NAME == develop_branch) { tagSuffix = "-SNAPSHOT" }

                    sh 'touch reg.txt'
                    sh 'touch argo.txt'
                    def sha = sh(script: "docker images --digests | grep '${docker_url}/ci${as_code}/ci${fp_code}/.*${vers}_${appComponent}${BUILD_ID}${tagSuffix}.*'", returnStdout: true)
                    def img = 'sha256:' + sha.toString().replaceAll(/.*sha256:/, "").replaceAll(/\s.*/, "")
                    def reg = ''
                    if (env.BRANCH_NAME == develop_branch) {
                        sh "echo 'docker-dev.registry-ci.delta.sbrf.ru/ci${as_code}/ci${fp_code}/${appComponent}:D-${vers}_${appComponent}${BUILD_ID}${tagSuffix}@${img}' >> reg.txt"
                        reg = "docker-dev.registry-ci.delta.sbrf.ru/ci${as_code}/ci${fp_code}/${appComponent}:D-${vers}_${appComponent}${BUILD_ID}${tagSuffix}@${img}"
                    } else {
                        sh "echo 'registry.sigma.sbrf.ru/ci${as_code}/ci${fp_code}/${appComponent}:D-${vers}_${appComponent}${BUILD_ID}${tagSuffix}@${img}' >> reg.txt"
                        reg = "registry.sigma.sbrf.ru/ci${as_code}/ci${fp_code}/${appComponent}:D-${vers}_${appComponent}${BUILD_ID}${tagSuffix}@${img}"
                    }
                    sh "echo '${appImg}: ${appComponent}@${img}' >> argo.txt"
                    def argo = "${appImg}: ${appComponent}@${img}"
                    sh 'cat reg.txt'
                    sh 'cat argo.txt'

                    /*withCredentials([usernamePassword(
                        credentialsId: tuz_ci,
                        usernameVariable: 'USERNAME',
                        passwordVariable: 'PASSWORD'
                    )]) {
                        sh """
                            git clone https://\${USERNAME}:\${PASSWORD}@stash.delta.sbrf.ru/scm/aimis/aimis-patches.git
                            cd aimis-patches/
                            git fetch --all
                            bash -c 'git branch -avv'
                            cd apps_docker_urls/
                            rm --force ${appComponent}.txt
                            touch ${appComponent}.txt
                            echo '${reg}' >> ${appComponent}.txt
                            cd ../
                            cd deploy_argo/
                            rm --force ${appComponent}.txt
                            touch ${appComponent}.txt
                            echo '${argo}' >> ${appComponent}.txt
                            cd ../
                            git add .
                            git commit -m "Auto update by Jenkins: New images"  
                            git push https://\${USERNAME}:\${PASSWORD}@stash.delta.sbrf.ru/scm/aimis/aimis-patches.git HEAD
                        """
                    }*/

                    archiveArtifacts artifacts: 'reg.txt', fingerprint: true

                    echo "###### Stage Distributive name (SHA256) SUCCESS ######"
                }
            }
        }

        stage('Release Notes') {
            when {
                anyOf {
                    branch master_branch 
                }
            }
            steps {
                script {
                    echo "###### Push release notes for ${appComponent} image ######"

                    prev_release = sh (
                        script: 'git branch --list *origin/release/* -a | grep ${BRANCH_NAME} -B 1 | head -n 1',
                        returnStdout: true
                    ).trim()
                    rn = releaseNotes()
                        .setArtifactRepository("registry")
                        .setGroup("CI${as_code}")
                        .setArtifact("CI${fp_code}/${appComponent}")
                        .setVersion("D-${vers}_${appComponent}${BUILD_ID}")
                        .setQgmCredsId("${tuz_ci}")
                        .addRepoViaBitbucketAPI(
                            "${PROJECT}",
                            "${repo}",
                            "${bitbucket_url}",
                            "${tuz_ci}",
                            true,
                            prev_release,
                            env.GIT_COMMIT
                        )
                        .createAndUploadReleaseNotes()

                    echo "###### Stage Release Notes SUCCESS ######"
                }
            }
        }

        stage('Quality Gate CI OK Flag') {
            when {
                anyOf {
                    branch master_branch 
                }
            }
            steps {
                script {
                    echo "####### Push CI_OK flag to QG for ${appComponent} #######"

                    qg = qualityGates()
                            .setArtifactRepository("registry")
                            .setGroup("CI${as_code}")
                            .setArtifact("CI${fp_code}/${appComponent}")
                            .setVersion("D-${vers}_${appComponent}${BUILD_ID}")
                            .setQgmCredsId("${tuz_ci}")
                            .uploadFlag("ci", "ok")

                    echo "####### Stage Quality Gate CI OK Flag SUCCESS #######"
                }
            }
        }
    }
	        
    post {
        always {
            cleanWs disableDeferredWipeout: true, deleteDirs: true
        }
    }
}
