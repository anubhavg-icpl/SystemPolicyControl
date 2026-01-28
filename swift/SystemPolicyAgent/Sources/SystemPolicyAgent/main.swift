import Foundation

struct AgentConfig {
    var allowIdentifiedDevelopers: Bool = true
    var enableAssessment: Bool = true
    var enableXProtectMalwareUpload: Bool = true
    var profileIdentifier: String = "com.systempolicycontrol.policy"
    var displayName: String = "System Policy Control"
    var organization: String = "SystemPolicyControl"
    var description: String? = nil
    var profileDirectory: URL = AgentConfig.defaultProfilesDirectory()
    var statePath: URL = AgentConfig.defaultStatePath()
    var installProfile: Bool = true

    static func defaultProfilesDirectory() -> URL {
        let cwd = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        return cwd.appendingPathComponent("data/profiles", isDirectory: true)
    }

    static func defaultStatePath() -> URL {
        let cwd = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
        return cwd.appendingPathComponent("data/policy_state.json", isDirectory: false)
    }
}

struct InstallResult {
    let succeeded: Bool
    let stdout: String?
    let stderr: String?
}

enum AgentError: Error, CustomStringConvertible {
    case invalidArguments(String)
    case failedToWriteProfile(String)
    case failedToWriteState(String)

    var description: String {
        switch self {
        case .invalidArguments(let message):
            return message
        case .failedToWriteProfile(let message):
            return message
        case .failedToWriteState(let message):
            return message
        }
    }
}

func resolvePath(_ path: String) -> URL {
    let expanded = (path as NSString).expandingTildeInPath
    if expanded.hasPrefix("/") {
        return URL(fileURLWithPath: expanded)
    }
    let cwd = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    return cwd.appendingPathComponent(expanded)
}

func parseBool(_ value: String) -> Bool? {
    switch value.lowercased() {
    case "true", "1", "yes":
        return true
    case "false", "0", "no":
        return false
    default:
        return nil
    }
}

func printUsage() {
    let usage = """
    Usage: system-policy-agent <action> [options]

    Actions:
      apply                               Generate and optionally install a Gatekeeper profile
      remove <identifier>                 Remove a profile by identifier
      list                                List installed profiles

    Options for 'apply':
      --profile-dir <path>                Directory to write generated .mobileconfig files (default: data/profiles)
      --state-path <path>                 JSON file that tracks the last applied policy (default: data/policy_state.json)
      --profile-identifier <value>        Base identifier stored in the payload (default: com.systempolicycontrol.policy)
      --display-name <value>              Payload display name (default: System Policy Control)
      --organization <value>             Organization string embedded in the profile
      --description <value>              Optional description included in the profile
      --allow-identified-developers <bool>
      --enable-assessment <bool>
      --enable-xprotect-malware-upload <bool>
      --no-install                        Generate the profile without calling the profiles command

    Options for 'remove':
      --profile-dir <path>                Directory containing the profile (default: data/profiles)
      --state-path <path>                 JSON file tracking policy state (default: data/policy_state.json)

    Global options:
      --help                              Show this message
    """
    print(usage)
}

enum AgentAction {
    case apply(AgentConfig)
    case remove(identifier: String, profileDirectory: URL, statePath: URL)
    case list
}

func parseArguments() throws -> AgentAction {
    var args = CommandLine.arguments
    guard args.count >= 2 else {
        throw AgentError.invalidArguments("Missing action. Expected 'apply', 'remove', or 'list'.")
    }

    _ = args.removeFirst() // executable name
    let action = args.removeFirst()
    if action == "--help" || action == "-h" {
        printUsage()
        exit(EXIT_SUCCESS)
    }

    switch action {
    case "apply":
        var config = AgentConfig()
        var index = 0
        while index < args.count {
            let arg = args[index]
            switch arg {
            case "--help", "-h":
                printUsage()
                exit(EXIT_SUCCESS)
            case "--profile-dir":
                index += 1
                guard index < args.count else { throw AgentError.invalidArguments("--profile-dir requires a value") }
                config.profileDirectory = resolvePath(args[index])
            case "--state-path":
                index += 1
                guard index < args.count else { throw AgentError.invalidArguments("--state-path requires a value") }
                config.statePath = resolvePath(args[index])
            case "--profile-identifier":
                index += 1
                guard index < args.count else { throw AgentError.invalidArguments("--profile-identifier requires a value") }
                config.profileIdentifier = args[index]
            case "--display-name":
                index += 1
                guard index < args.count else { throw AgentError.invalidArguments("--display-name requires a value") }
                config.displayName = args[index]
            case "--organization":
                index += 1
                guard index < args.count else { throw AgentError.invalidArguments("--organization requires a value") }
                config.organization = args[index]
            case "--description":
                index += 1
                guard index < args.count else { throw AgentError.invalidArguments("--description requires a value") }
                config.description = args[index]
            case "--allow-identified-developers":
                index += 1
                guard index < args.count, let parsed = parseBool(args[index]) else {
                    throw AgentError.invalidArguments("--allow-identified-developers requires true/false")
                }
                config.allowIdentifiedDevelopers = parsed
            case "--enable-assessment":
                index += 1
                guard index < args.count, let parsed = parseBool(args[index]) else {
                    throw AgentError.invalidArguments("--enable-assessment requires true/false")
                }
                config.enableAssessment = parsed
                if !parsed {
                    config.allowIdentifiedDevelopers = false
                }
            case "--enable-xprotect-malware-upload":
                index += 1
                guard index < args.count, let parsed = parseBool(args[index]) else {
                    throw AgentError.invalidArguments("--enable-xprotect-malware-upload requires true/false")
                }
                config.enableXProtectMalwareUpload = parsed
            case "--no-install":
                config.installProfile = false
            default:
                throw AgentError.invalidArguments("Unknown argument: \(arg)")
            }
            index += 1
        }
        return .apply(config)

    case "remove":
        guard args.count >= 1 else {
            throw AgentError.invalidArguments("remove action requires a profile identifier")
        }
        let identifier = args.removeFirst()
        var profileDirectory = AgentConfig.defaultProfilesDirectory()
        var statePath = AgentConfig.defaultStatePath()
        var index = 0
        while index < args.count {
            let arg = args[index]
            switch arg {
            case "--profile-dir":
                index += 1
                guard index < args.count else { throw AgentError.invalidArguments("--profile-dir requires a value") }
                profileDirectory = resolvePath(args[index])
            case "--state-path":
                index += 1
                guard index < args.count else { throw AgentError.invalidArguments("--state-path requires a value") }
                statePath = resolvePath(args[index])
            default:
                throw AgentError.invalidArguments("Unknown argument for remove: \(arg)")
            }
            index += 1
        }
        return .remove(identifier: identifier, profileDirectory: profileDirectory, statePath: statePath)

    case "list":
        if !args.isEmpty {
            throw AgentError.invalidArguments("list action does not take any arguments")
        }
        return .list

    default:
        throw AgentError.invalidArguments("Unsupported action: \(action)")
    }
}

func buildProfilePayload(config: AgentConfig) -> [String: Any] {
    var payload: [String: Any] = [
        "EnableAssessment": config.enableAssessment,
        "EnableXProtectMalwareUpload": config.enableXProtectMalwareUpload,
        "PayloadType": "com.apple.systempolicy.control",
        "PayloadVersion": 1,
        "PayloadIdentifier": "\(config.profileIdentifier).payload",
        "PayloadUUID": UUID().uuidString
    ]
    if config.enableAssessment {
        payload["AllowIdentifiedDevelopers"] = config.allowIdentifiedDevelopers
    }

    let profile: [String: Any] = [
        "PayloadContent": [payload],
        "PayloadDescription": config.description ?? "Generated by SystemPolicyAgent.",
        "PayloadDisplayName": config.displayName,
        "PayloadIdentifier": config.profileIdentifier,
        "PayloadOrganization": config.organization,
        "PayloadRemovalDisallowed": true,
        "PayloadType": "Configuration",
        "PayloadUUID": UUID().uuidString,
        "PayloadVersion": 1
    ]
    return profile
}

@discardableResult
func writeProfile(_ profile: [String: Any], to directory: URL, identifier: String) throws -> URL {
    let fileManager = FileManager.default
    try fileManager.createDirectory(at: directory, withIntermediateDirectories: true, attributes: nil)
    let filename = "\(identifier)-\(UUID().uuidString).mobileconfig"
    let destination = directory.appendingPathComponent(filename)
    let data = try PropertyListSerialization.data(fromPropertyList: profile, format: .xml, options: 0)
    try data.write(to: destination)
    return destination
}

func installProfile(at url: URL, shouldInstall: Bool) -> InstallResult {
    guard shouldInstall else {
        return InstallResult(succeeded: false, stdout: nil, stderr: "Installation skipped (no-install)")
    }

    #if os(macOS)
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/profiles")
    process.arguments = ["install", "-type", "configuration", "-path", url.path]

    let stdoutPipe = Pipe()
    process.standardOutput = stdoutPipe
    let stderrPipe = Pipe()
    process.standardError = stderrPipe

    do {
        try process.run()
        process.waitUntilExit()
    } catch {
        return InstallResult(succeeded: false, stdout: nil, stderr: "Failed to invoke profiles: \(error)")
    }

    let stdoutData = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
    let stderrData = stderrPipe.fileHandleForReading.readDataToEndOfFile()
    let stdoutString = String(data: stdoutData, encoding: .utf8)
    let stderrString = String(data: stderrData, encoding: .utf8)
    let success = process.terminationStatus == 0
    return InstallResult(succeeded: success, stdout: stdoutString, stderr: stderrString)
    #else
    return InstallResult(succeeded: false, stdout: nil, stderr: "Profile installation supported only on macOS")
    #endif
}

func removeProfile(withIdentifier identifier: String) -> InstallResult {
    #if os(macOS)
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/profiles")
    process.arguments = ["-R", "-p", identifier]

    let stdoutPipe = Pipe()
    process.standardOutput = stdoutPipe
    let stderrPipe = Pipe()
    process.standardError = stderrPipe

    do {
        try process.run()
        process.waitUntilExit()
    } catch {
        return InstallResult(succeeded: false, stdout: nil, stderr: "Failed to invoke profiles: \(error)")
    }

    let stdoutData = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
    let stderrData = stderrPipe.fileHandleForReading.readDataToEndOfFile()
    let stdoutString = String(data: stdoutData, encoding: .utf8)
    let stderrString = String(data: stderrData, encoding: .utf8)
    let success = process.terminationStatus == 0
    return InstallResult(succeeded: success, stdout: stdoutString, stderr: stderrString)
    #else
    return InstallResult(succeeded: false, stdout: nil, stderr: "Profile removal supported only on macOS")
    #endif
}

func listProfiles() -> [[String: Any]]? {
    #if os(macOS)
    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/profiles")
    process.arguments = ["-C", "-o", "stdout"]

    let stdoutPipe = Pipe()
    process.standardOutput = stdoutPipe
    let stderrPipe = Pipe()
    process.standardError = stderrPipe

    do {
        try process.run()
        process.waitUntilExit()
    } catch {
        return []
    }

    let stdoutData = stdoutPipe.fileHandleForReading.readDataToEndOfFile()

    if stdoutData.isEmpty {
        return []
    }

    guard let profiles = try? PropertyListSerialization.propertyList(from: stdoutData, options: [], format: nil) as? [[String: Any]] else {
        return []
    }
    return profiles
    #else
    return nil
    #endif
}

func deleteState(at path: URL) throws {
    let fileManager = FileManager.default
    if fileManager.fileExists(atPath: path.path) {
        try fileManager.removeItem(at: path)
    }
}

func deleteProfileFile(at path: URL) throws {
    let fileManager = FileManager.default
    if fileManager.fileExists(atPath: path.path) {
        try fileManager.removeItem(at: path)
    }
}

func writeState(config: AgentConfig, profilePath: URL, installResult: InstallResult) throws {
    let fileManager = FileManager.default
    try fileManager.createDirectory(at: config.statePath.deletingLastPathComponent(), withIntermediateDirectories: true, attributes: nil)

    var policyDict: [String: Any] = [
        "allow_identified_developers": config.allowIdentifiedDevelopers,
        "enable_assessment": config.enableAssessment,
        "enable_xprotect_malware_upload": config.enableXProtectMalwareUpload,
        "profile_identifier": config.profileIdentifier,
        "display_name": config.displayName,
        "organization": config.organization
    ]
    if let description = config.description {
        policyDict["description"] = description
    }

    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

    var state: [String: Any] = [
        "policy": policyDict,
        "profile_path": profilePath.path,
        "applied_at": formatter.string(from: Date()),
        "install_attempted": config.installProfile,
        "install_succeeded": installResult.succeeded
    ]
    if let stdout = installResult.stdout {
        state["installer_stdout"] = stdout
    } else {
        state["installer_stdout"] = NSNull()
    }
    if let stderr = installResult.stderr {
        state["installer_stderr"] = stderr
    } else {
        state["installer_stderr"] = NSNull()
    }

    let data = try JSONSerialization.data(withJSONObject: state, options: [.prettyPrinted, .sortedKeys])
    try data.write(to: config.statePath)
}

func runAgent() -> Int32 {
    do {
        let action = try parseArguments()

        switch action {
        case .apply(let config):
            let profile = buildProfilePayload(config: config)
            let profilePath = try writeProfile(profile, to: config.profileDirectory, identifier: config.profileIdentifier)
            let installResult = installProfile(at: profilePath, shouldInstall: config.installProfile)
            try writeState(config: config, profilePath: profilePath, installResult: installResult)
            if installResult.succeeded || !config.installProfile {
                print("Profile generated at \(profilePath.path)")
                return EXIT_SUCCESS
            } else {
                fputs("Profile installation failed: \(installResult.stderr ?? "unknown error")\n", stderr)
                return EXIT_FAILURE
            }

        case .remove(let identifier, let profileDirectory, let statePath):
            let removeResult = removeProfile(withIdentifier: identifier)
            let fileManager = FileManager.default

            if let files = try? fileManager.contentsOfDirectory(at: profileDirectory, includingPropertiesForKeys: nil) {
                for file in files where file.path.contains(identifier) {
                    try? fileManager.removeItem(at: file)
                }
            }

            try deleteState(at: statePath)

            if removeResult.succeeded {
                print("Profile removed successfully")
                return EXIT_SUCCESS
            } else {
                let errorOutput = removeResult.stderr ?? "unknown error"
                if errorOutput.isEmpty {
                    print("Profile removed from disk")
                    return EXIT_SUCCESS
                }
                fputs("Profile removal failed: \(errorOutput)\n", stderr)
                return EXIT_FAILURE
            }

        case .list:
            if let profiles = listProfiles() {
                let jsonData: Data
                if profiles.isEmpty {
                    jsonData = try JSONSerialization.data(withJSONObject: profiles, options: [.sortedKeys])
                } else {
                    jsonData = try JSONSerialization.data(withJSONObject: profiles, options: [.prettyPrinted, .sortedKeys])
                }
                if let jsonString = String(data: jsonData, encoding: .utf8) {
                    print(jsonString)
                }
                return EXIT_SUCCESS
            } else {
                print("[]")
                return EXIT_SUCCESS
            }
        }

    } catch let error as AgentError {
        fputs("Error: \(error.description)\n", stderr)
        printUsage()
        return EXIT_FAILURE
    } catch {
        fputs("Unexpected error: \(error.localizedDescription)\n", stderr)
        return EXIT_FAILURE
    }
}

exit(runAgent())
