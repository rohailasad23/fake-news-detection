// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title NewsRegistry
/// @notice Tamper-proof ledger of analysed news items and their sources.
///         Each record is keyed by the keccak256 hash of the normalised news text, so
///         the first registration of a piece of content permanently fixes its origin.
contract NewsRegistry {
    struct NewsRecord {
        bytes32 contentHash;   // unique hash of the news content
        string source;         // claimed source (publisher / domain / author)
        string sourceUrl;      // optional link to the original article
        string label;          // AI classification at registration time ("Real" / "Fake")
        uint16 confidence;     // AI confidence in basis points (0 - 10000)
        string modelName;      // model that produced the classification
        uint256 timestamp;     // block time of registration
        address submitter;     // account that registered the record
    }

    address public owner;
    mapping(bytes32 => NewsRecord) private records;
    bytes32[] private recordHashes;
    mapping(bytes32 => bool) private trustedSources;   // keccak256(lower-cased source) => trusted
    string[] private trustedSourceList;

    event NewsRegistered(bytes32 indexed contentHash, string source, string label, uint16 confidence,
                         address indexed submitter, uint256 timestamp);
    event SourceTrusted(string source);
    event SourceRevoked(string source);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // ------------------------------------------------------------ news records
    function registerNews(
        bytes32 contentHash,
        string calldata source,
        string calldata sourceUrl,
        string calldata label,
        uint16 confidence,
        string calldata modelName
    ) external {
        require(contentHash != bytes32(0), "Empty hash");
        require(records[contentHash].timestamp == 0, "Already registered");
        require(confidence <= 10000, "Invalid confidence");
        records[contentHash] = NewsRecord(contentHash, source, sourceUrl, label, confidence,
                                          modelName, block.timestamp, msg.sender);
        recordHashes.push(contentHash);
        emit NewsRegistered(contentHash, source, label, confidence, msg.sender, block.timestamp);
    }

    function isRegistered(bytes32 contentHash) external view returns (bool) {
        return records[contentHash].timestamp != 0;
    }

    function getRecord(bytes32 contentHash) external view returns (NewsRecord memory) {
        require(records[contentHash].timestamp != 0, "Not found");
        return records[contentHash];
    }

    function recordCount() external view returns (uint256) {
        return recordHashes.length;
    }

    function recordHashAt(uint256 index) external view returns (bytes32) {
        return recordHashes[index];
    }

    // ------------------------------------------------------------ trusted sources
    function addTrustedSource(string calldata source) external onlyOwner {
        bytes32 key = keccak256(bytes(source));
        if (!trustedSources[key]) {
            trustedSources[key] = true;
            trustedSourceList.push(source);
            emit SourceTrusted(source);
        }
    }

    function removeTrustedSource(string calldata source) external onlyOwner {
        bytes32 key = keccak256(bytes(source));
        require(trustedSources[key], "Not trusted");
        trustedSources[key] = false;
        for (uint256 i = 0; i < trustedSourceList.length; i++) {
            if (keccak256(bytes(trustedSourceList[i])) == key) {
                trustedSourceList[i] = trustedSourceList[trustedSourceList.length - 1];
                trustedSourceList.pop();
                break;
            }
        }
        emit SourceRevoked(source);
    }

    function isTrustedSource(string calldata source) external view returns (bool) {
        return trustedSources[keccak256(bytes(source))];
    }

    function getTrustedSources() external view returns (string[] memory) {
        return trustedSourceList;
    }
}
