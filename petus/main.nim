import streams
import tables

type
  BreakOutOfLoops = object of Exception

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
            result[y][z][x] = blockToId["dirt"]
          of 74:
            result[y][z][x] = blockToId["grass"]
          else:
            result[y][z][x] = blockToId["air"]

proc dumpToObjFile(file: FileStream, chunk: array[0..256, array[0..16, array[0..16, int]]]) =
  var points: seq[tuple[x: int, y: int, z: int]]
  var faces: seq[string]

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
          if not (p in points):
            points.add(p)

  # add faces
  for y in countup(0, 255):
    for z in countup(0, 15):
      for x in countup(0, 15):
        let blockId = chunk[y][z][x]

        if blockId == blockToId["air"]:
          continue

        var visible = false

        if z == 0 or x == 0:
          visible = true
        else:
          try:
            for y2 in [y - 1, y + 1]:
              for z2 in [z - 1, z + 1]:
                for x2 in [x - 1, x + 1]:
                  if chunk[y2][z2][x2] == 0:
                    visible = true
                    raise newException(BreakOutOfLoops, "yeet")
          except BreakOutOfLoops:
            discard

        if not visible:
          continue

        let blockName = idToBlock[blockId]

        let tx = x + cxo
        let tz = z + czo

        let i1 = points.find((tx, y, tz)) + 1
        let i2 = points.find((tx + 1, y, tz)) + 1
        let i3 = points.find((tx, y + 1, tz)) + 1
        let i4 = points.find((tx, y, tz + 1)) + 1
        let i5 = points.find((tx + 1, y + 1, tz)) + 1
        let i6 = points.find((tx, y + 1, tz + 1)) + 1
        let i7 = points.find((tx + 1, y, tz + 1)) + 1
        let i8 = points.find((tx + 1, y + 1, tz + 1)) + 1

        let fs = [
          "usemtl " + blockName + ""
        ]
