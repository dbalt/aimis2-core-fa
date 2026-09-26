// Shared Jenkins version and release-tag operations.
String versionTagPrefix(String component) {
    return "jenkins-version/${component}/v"
}

String bumpVersion(String version, String mode) {
    def matcher = version =~ /^(\d{2})\.(\d{3})\.(\d{2})$/
    if (!matcher.matches()) {
        error("Unsupported version '${version}'. Expected format: 01.000.01")
    }

    int major = matcher[0][1].toInteger()
    int minor = matcher[0][2].toInteger()
    int patch = matcher[0][3].toInteger()

    switch (mode) {
        case 'none':
            return version
        case 'patch':
            patch += 1
            if (patch > 99) {
                patch = 0
                minor += 1
            }
            break
        case 'minor':
            minor += 1
            patch = 0
            break
        case 'major':
            major += 1
            minor = 0
            patch = 0
            break
        default:
            error("Unsupported VERSION_BUMP '${mode}'")
    }

    if (minor > 999) {
        minor = 0
        major += 1
    }
    if (major > 99) {
        error('Version major component exceeded 99')
    }

    return "${major.toString().padLeft(2, '0')}.${minor.toString().padLeft(3, '0')}.${patch.toString().padLeft(2, '0')}"
}

String resolveVersion(
    String component,
    String fallbackVersion,
    String bumpMode,
    boolean releaseBuild,
    String repositoryUrl,
    String credentialsId
) {
    String prefix = versionTagPrefix(component)
    String latestVersion = ''

    withCredentials([
        usernamePassword(
            credentialsId: credentialsId,
            usernameVariable: 'VERSION_GIT_USERNAME',
            passwordVariable: 'VERSION_GIT_PASSWORD'
        )
    ]) {
        String authenticatedUrl = repositoryUrl.replace(
            'https://',
            'https://${VERSION_GIT_USERNAME}:${VERSION_GIT_PASSWORD}@'
        )
        latestVersion = sh(
            script: """#!/bin/bash
                set +x
                git ls-remote --tags --refs "${authenticatedUrl}" "refs/tags/${prefix}*" \\
                    | awk '{print \$2}' \\
                    | sed 's#refs/tags/${prefix}##' \\
                    | sort -V \\
                    | tail -n 1
            """,
            returnStdout: true
        ).trim()
    }

    String baseVersion = latestVersion ?: fallbackVersion
    // Validate the persisted/fallback value even for non-release builds.
    String validatedVersion = bumpVersion(baseVersion, 'none')
    return releaseBuild ? bumpVersion(validatedVersion, bumpMode ?: 'patch') : validatedVersion
}

void publishReleaseTag(
    String component,
    String version,
    String repositoryUrl,
    String credentialsId
) {
    String tag = "${versionTagPrefix(component)}${version}"

    withCredentials([
        usernamePassword(
            credentialsId: credentialsId,
            usernameVariable: 'VERSION_GIT_USERNAME',
            passwordVariable: 'VERSION_GIT_PASSWORD'
        )
    ]) {
        String authenticatedUrl = repositoryUrl.replace(
            'https://',
            'https://${VERSION_GIT_USERNAME}:${VERSION_GIT_PASSWORD}@'
        )
        int exists = sh(
            script: """#!/bin/bash
                set +x
                git ls-remote --exit-code --tags --refs "${authenticatedUrl}" "refs/tags/${tag}" >/dev/null 2>&1
            """,
            returnStatus: true
        )
        if (exists == 0) {
            echo "Version tag ${tag} already exists; skipping publication"
            return
        }

        sh """#!/bin/bash
            set +x
            git tag -a '${tag}' -m 'Jenkins release ${component} ${version}'
            git push "${authenticatedUrl}" 'refs/tags/${tag}'
        """
        echo "Published version tag ${tag}"
    }
}

return this
