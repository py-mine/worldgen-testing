import streams
import hashes
import tables

type
  BreakOutOfLoops = object of CatchableError
  Point = tuple[x: int, y: int, z: int]

let blockToId = {
  "air": 0,
  "bedrock": 1,
  "stone": 2,
  "dirf": 3,
  "grass": 4,
  "water": 5
}.newTable

let idToBlock = {
  0: "air",
  1: "bedrock",
  2: "stone",
  3: "dirf",
  4: "grass",
  5: "water"
}.newTable

proc newBlankChunk(): array[0..256, array[0..16, array[0..16, int]]] =
  for y in countup(0, 255):
    for z in countup(0, 15):
      for x in countup(0, 15):
        case y:
          of 0..4:
            result[y][z][x] = blockToId["bedrock"]
          of 5..69:
            result[y][z][x] = blockToId["stone"]
          of 70..73:
            result[y][z][x] = blockToId["dirf"]
          of 74:
            result[y][z][x] = blockToId["grass"]
          else:
            result[y][z][x] = blockToId["air"]

proc fmtFace(a: int, b: int, c: int, d: int): string =
  return "f " & $a & " " & $b & " " & $c & " " & $d

proc fmtPoint(p: Point): string =
  return "v " & $p.x & " " & $p.y & " " & $p.z

proc dumpToObjFile(file: FileStream, chunk: array[0..256, array[0..16, array[0..16, int]]]) {.discardable.} =
  var points: seq[Point]
  var rPoints = initTable[Point, int]()
  var faces: seq[string]
  var rFaces = initTable[string, int]()

  proc appendPoint(p: Point) =
    if rPoints.getOrDefault(p, -1) == -1:
      points.add(p)
      rPoints[p] = len(points) - 1

  proc appendFace(f: string) =
    if rFaces.getOrDefault(f, -1) == -1:
      faces.add(f)
      rFaces[f] = len(faces) - 1

  # used to deal with chunk offset, not needed here rn but will be later
  let cxo = 0 * 16
  let czo = 0 * 16

  # add points
  for y in countup(0, 255):
    for z in countup(0, 15):
      for x in countup(0, 15):
        if chunk[y][z][x] == blockToId["air"]:
          continue

        let tx = x + cxo
        let tz = z + czo

        let ps = [
          (tx, y, tz),
          (tx + 1, y, tz),
          (tx, y + 1, tz),
          (tx, y, tz + 1),
          (tx + 1, y + 1, tz),
          (tx, y + 1, tz + 1),
          (tx + 1, y, tz + 1),
          (tx + 1, y + 1, tz + 1)
        ]

        for p in ps:
          appendPoint(p)

  # add faces
  for y in countup(0, 255):
    for z in countup(0, 15):
      for x in countup(0, 15):
        let blockId = chunk[y][z][x]

        if blockId == blockToId["air"]:
          continue

        var visible = false

        if y == 0 or z == 0 or x == 0:
          visible = true
        else:
          try:
            for y2 in [y - 1, y + 1]:
              for z2 in [z - 1, z + 1]:
                for x2 in [x - 1, x + 1]:
                  try:
                    if chunk[y2][z2][x2] == 0:
                      visible = true
                      raise newException(BreakOutOfLoops, "yeet")
                  except IndexDefect:
                    discard
          except BreakOutOfLoops:
            discard

        if not visible:
          continue

        let blockName = idToBlock[blockId]

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

        let fs = [
          "usemtl " & blockName & "\n" & fmtFace(i1, i2, i7, i4),
          fmtFace(i1, i2, i5, i3),
          fmtFace(i4, i7, i8, i6),
          fmtFace(i1, i4, i6, i3),
          fmtFace(i2, i5, i8, i7),
          fmtFace(i3, i5, i8, i6)
        ]

        for f in fs:
          appendFace(f)

  for p in points:
    file.writeLine(fmtPoint(p))

  for face in faces:
    file.writeLine(face)


var file = newFileStream("test.obj", fmWrite)
echo "Creating new chunk..."
var chunk = newBlankChunk()

echo "Dumping to file..."
dumpToObjFile(file, chunk)
