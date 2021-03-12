import strutils
import streams
import hashes
import tables
import times
import math
import os

template benchmark(benchmarkName: string, code: untyped) =
  block:
    let t0 = epochTime()
    code
    let elapsed = epochTime() - t0
    let elapsedStr = elapsed.formatFloat(format = ffDecimal, precision = 3)
    echo "Elapsed time: [", benchmarkName, "]: ", elapsedStr, " seconds"

type
  BreakOutOfLoops = object of Defect

  Point = tuple[x: int, y: int, z: int]

  Chunk = array[0..256, array[0..16, array[0..16, int]]]

let blockToId = {
  "air": 0,
  "bedrock": 1,
  "stone": 2,
  "dirt": 3,
  "grass": 4,
  "water": 5
}.newTable

let idToBlock = {
  0: "air",
  1: "bedrock",
  2: "stone",
  3: "dirt",
  4: "grass",
  5: "water"
}.newTable

proc newBlankChunk(): Chunk =
  for y in countup(0, 255):
    for z in countup(0, 15):
      for x in countup(0, 15):
        case y:
          of 0..4:
            result[y][z][x] = blockToId["bedrock"]
          of 5..69:
            result[y][z][x] = blockToId["stone"]
          of 70..73:
            result[y][z][x] = blockToId["dirt"]
          of 74:
            result[y][z][x] = blockToId["grass"]
          else:
            result[y][z][x] = blockToId["air"]

proc fmtFace(a: int, b: int, c: int, d: int): string =
  return "f " & $a & " " & $b & " " & $c & " " & $d

proc fmtPoint(p: Point): string =
  return "v " & $p.x & " " & $p.y & " " & $p.z

proc dumpToObjFile(file: FileStream, chunks: Table[tuple[x: int, z: int], Chunk]) {.discardable.} =
  var points: seq[Point]
  var rPoints: Table[Point, int] = initTable[Point, int]()
  var pointCount: int = 0

  var faces: seq[string]
  var rFaces: Table[string, int] = initTable[string, int]()
  var faceCount: int = 0

  proc appendPoint(px: int, py: int, pz: int) =
    let p = (px, py, pz)

    if rPoints.getOrDefault(p, -1) == -1:
      points.add(p)
      pointCount += 1
      rPoints[p] = pointCount

  proc appendFace(f: string) =
    if rFaces.getOrDefault(f, -1) == -1:
      faces.add(f)
      faceCount += 1
      rFaces[f] = faceCount

  for cx, cz in chunks.keys():
    let chunk = chunks[(cx, cz)]

    let cxo = cx * 16
    let czo = cz * 16

    # add points
    benchmark "Points Calculation":
      for y in countup(0, 255):
        for z in countup(0, 15):
          for x in countup(0, 15):
            if chunk[y][z][x] == blockToId["air"]:
              continue

            let tx = x + cxo
            let tz = z + czo

            appendPoint(tx, y, tz)
            appendPoint(tx + 1, y, tz)
            appendPoint(tx, y + 1, tz)
            appendPoint(tx, y, tz + 1)
            appendPoint(tx + 1, y + 1, tz)
            appendPoint(tx, y + 1, tz + 1)
            appendPoint(tx + 1, y, tz + 1)
            appendPoint(tx + 1, y + 1, tz + 1)

    # add faces
    benchmark "Faces Calculation":
      for y in countup(0, 255):
        for z in countup(0, 15):
          for x in countup(0, 15):
            if chunk[y][z][x] == 0:  # air
              continue

            try:
              for y2 in [y-1, y+1]:
                for z2 in [z-1, z+1]:
                  for x2 in [x-1, x+1]:
                    try:
                      if chunk[y2][z2][x2] == 0:
                        let tx = x + cxo
                        let tz = z + czo

                        let i1 = rpoints[(tx, y, tz)] + 1
                        let i2 = rpoints[(tx + 1, y, tz)] + 1
                        let i3 = rpoints[(tx, y + 1, tz)] + 1
                        let i4 = rpoints[(tx, y, tz + 1)] + 1
                        let i5 = rpoints[(tx + 1, y + 1, tz)] + 1
                        let i6 = rpoints[(tx, y + 1, tz + 1)] + 1
                        let i7 = rpoints[(tx + 1, y, tz + 1)] + 1
                        let i8 = rpoints[(tx + 1, y + 1, tz + 1)] + 1

                        appendFace("usemtl " & idToBlock[chunk[y][z][x]] & "\n" & fmtFace(i1, i2, i7, i4))
                        appendFace(fmtFace(i1, i2, i5, i3))
                        appendFace(fmtFace(i4, i7, i8, i6))
                        appendFace(fmtFace(i1, i4, i6, i3))
                        appendFace(fmtFace(i2, i5, i8, i7))
                        appendFace(fmtFace(i3, i5, i8, i6))

                        raise BreakOutOfLoops.newException "yeet"
                    except IndexDefect:
                      discard
            except BreakOutOfLoops:
              discard

  for p in points:
    file.writeLine(fmtPoint(p))

  file.write(faces.join("\n"))


let radius = parseInt(commandLineParams()[0])
var chunks = initTable[tuple[x: int, z: int], Chunk]()

echo "Generating " & $math.pow(float(radius*2), 2.0) & " chunks..."
benchmark "Chunk Generation":
  for x in countup(-radius, radius):
    for z in countup(-radius, radius):
      chunks[(x, z)] = newBlankChunk()

var file = newFileStream("test.obj", fmWrite)

echo "Dumping to obj file..."
benchmark "Dump To File":
  dumpToObjFile(file, chunks)
  file.flush()
