#!/usr/bin/swift

import AppKit
import Foundation
import Vision

struct Box: Codable {
    let x: Double
    let y: Double
    let width: Double
    let height: Double
}

struct TextObservation: Codable {
    let text: String
    let confidence: Double
    let bounding_box_normalized: Box
}

struct CodeObservation: Codable {
    let symbology: String
    let payload: String?
    let bounding_box_normalized: Box
}

struct ImageObservation: Codable {
    let file_path: String
    let width: Int
    let height: Int
    let coordinate_origin: String
    let text_observations: [TextObservation]
    let code_observations: [CodeObservation]
}

struct ResultEnvelope: Codable {
    let schema_version: String
    let invocation_id: String
    let input_paths: [String]
    let observations: [ImageObservation]
}

func box(_ rect: CGRect) -> Box {
    return Box(
        x: Double(rect.origin.x),
        y: Double(rect.origin.y),
        width: Double(rect.size.width),
        height: Double(rect.size.height)
    )
}

let arguments = Array(CommandLine.arguments.dropFirst())
guard arguments.count >= 6,
      arguments[0] == "--result-file",
      arguments[2] == "--invocation-id",
      arguments[4] == "--" else {
    FileHandle.standardError.write(Data("usage: macos_vision_ocr.swift --result-file PATH --invocation-id HEX32 -- IMAGE [IMAGE ...]\n".utf8))
    exit(2)
}
let resultPath = arguments[1]
let invocationID = arguments[3]
let paths = Array(arguments.dropFirst(5))
let hexCharacters = CharacterSet(charactersIn: "0123456789abcdef")
guard !resultPath.isEmpty,
      invocationID.count == 32,
      invocationID.unicodeScalars.allSatisfy({ hexCharacters.contains($0) }),
      !paths.isEmpty else {
    FileHandle.standardError.write(Data("invalid result path, invocation id, or image list\n".utf8))
    exit(2)
}

let envLanguages = ProcessInfo.processInfo.environment["PACKAGING_OCR_LANGUAGES"] ?? "zh-Hans,en-US"
let languages = envLanguages.split(separator: ",").map { String($0).trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
var results: [ImageObservation] = []

for path in paths {
    let url = URL(fileURLWithPath: path)
    guard let image = NSImage(contentsOf: url) else {
        FileHandle.standardError.write(Data("cannot load image: \(path)\n".utf8))
        exit(3)
    }
    var proposed = CGRect(origin: .zero, size: image.size)
    guard let cgImage = image.cgImage(forProposedRect: &proposed, context: nil, hints: nil) else {
        FileHandle.standardError.write(Data("cannot decode image pixels: \(path)\n".utf8))
        exit(3)
    }

    let textRequest = VNRecognizeTextRequest()
    textRequest.recognitionLevel = .accurate
    textRequest.usesLanguageCorrection = false
    textRequest.recognitionLanguages = languages
    textRequest.minimumTextHeight = 0.002

    let barcodeRequest = VNDetectBarcodesRequest()
    let handler = VNImageRequestHandler(cgImage: cgImage, orientation: .up, options: [:])
    do {
        try handler.perform([textRequest, barcodeRequest])
    } catch {
        FileHandle.standardError.write(Data("Vision request failed for \(path): \(error)\n".utf8))
        exit(4)
    }

    var texts: [TextObservation] = []
    for observation in textRequest.results ?? [] {
        guard let candidate = observation.topCandidates(1).first else { continue }
        texts.append(TextObservation(
            text: candidate.string,
            confidence: Double(candidate.confidence),
            bounding_box_normalized: box(observation.boundingBox)
        ))
    }
    texts.sort {
        if abs($0.bounding_box_normalized.y - $1.bounding_box_normalized.y) > 0.002 {
            return $0.bounding_box_normalized.y > $1.bounding_box_normalized.y
        }
        return $0.bounding_box_normalized.x < $1.bounding_box_normalized.x
    }

    var codes: [CodeObservation] = []
    for observation in barcodeRequest.results ?? [] {
        codes.append(CodeObservation(
            symbology: observation.symbology.rawValue,
            payload: observation.payloadStringValue,
            bounding_box_normalized: box(observation.boundingBox)
        ))
    }

    results.append(ImageObservation(
        file_path: url.path,
        width: cgImage.width,
        height: cgImage.height,
        coordinate_origin: "bottom_left_normalized",
        text_observations: texts,
        code_observations: codes
    ))
}

let encoder = JSONEncoder()
encoder.outputFormatting = [.sortedKeys]
do {
    let envelope = ResultEnvelope(
        schema_version: "packaging-macos-vision-result.v1",
        invocation_id: invocationID,
        input_paths: paths,
        observations: results
    )
    let data = try encoder.encode(envelope)
    try data.write(to: URL(fileURLWithPath: resultPath), options: .atomic)
} catch {
    FileHandle.standardError.write(Data("result-file encode/write failed: \(error)\n".utf8))
    exit(5)
}
