// swift-tools-version:5.7
import PackageDescription

let package = Package(
    name: "SystemPolicyAgent",
    platforms: [
        .macOS(.v12)
    ],
    products: [
        .executable(name: "SystemPolicyAgent", targets: ["SystemPolicyAgent"])
    ],
    targets: [
        .executableTarget(name: "SystemPolicyAgent", path: "Sources")
    ]
)
