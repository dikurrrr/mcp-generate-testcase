import Foundation
import PDFKit
import Vision
import CoreGraphics

// Usage: swift ocr_pdf.swift <input.pdf> <output.txt>
let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: ocr_pdf.swift <input.pdf> <output.txt>\n".data(using: .utf8)!)
    exit(1)
}
let inPath = args[1]
let outPath = args[2]

guard let doc = PDFDocument(url: URL(fileURLWithPath: inPath)) else {
    FileHandle.standardError.write("cannot open pdf\n".data(using: .utf8)!)
    exit(1)
}

var result = ""
let scale: CGFloat = 2.5

for i in 0..<doc.pageCount {
    guard let page = doc.page(at: i) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let w = Int(bounds.width * scale)
    let h = Int(bounds.height * scale)
    guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.premultipliedFirst.rawValue) else { continue }
    ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
    ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
    ctx.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: ctx)
    guard let img = ctx.makeImage() else { continue }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["id-ID", "en-US"]
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    do { try handler.perform([request]) } catch { continue }

    var lines: [String] = []
    for obs in (request.results ?? []) {
        for cand in obs.topCandidates(1) {
            lines.append(cand.string)
        }
    }
    result += "\n\n<!-- page \(i + 1) -->\n"
    result += lines.joined(separator: "\n")
    FileHandle.standardError.write("page \(i + 1)/\(doc.pageCount)\n".data(using: .utf8)!)
}

try result.write(toFile: outPath, atomically: true, encoding: .utf8)
print("wrote \(outPath)")
