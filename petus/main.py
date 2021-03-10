from noise.perlin import SimplexNoise  # pip install noise
from time import perf_counter as pf
import numpy
import math
import sys


# here, a "chunk" refers to a 16x256x16 array of block states

palette = {
    "air": 0,
    "bedrock": 1,
    "stone": 2,
    "dirt": 3,
    "grass": 4,
    "water": 5
}

palette = {**palette, **{v: k for k, v in palette.items()}}


def blank_chunk() -> numpy.ndarray:  # used to test dumping to a obj file
    #                       y   z   x
    chunk = numpy.ndarray((256, 16, 16), numpy.uint32)  # kinda how chunks are stored in pymine
    chunk.fill(0)

    chunk[0:5] = palette["bedrock"]
    chunk[5:69] = palette["stone"]
    chunk[69:73] = palette["dirt"]
    chunk[73:74] = palette["grass"]

    return chunk.tolist()


def noisy_chunk(noise, chunk_x: int, chunk_z: int) -> numpy.ndarray:
    chunk = numpy.zeros((256, 16, 16), numpy.uint64)
    height_map = [[0]*16 for _ in range(16)]

    x_offset = 16 * chunk_x
    z_offset = 16 * chunk_z

    chunk[0] = palette["bedrock"]

    for y in range(4):
        for x in range(16):
            for z in range(16):
                n = noise.noise3(x, y, z)

                if y < 2:
                    if n >= 0:
                        chunk[y+1, z, x] = palette["bedrock"]
                elif n > 0:
                    chunk[y+1, z, x] = palette["bedrock"]

    freq = 16
    octv1 = 2
    octv2 = 4
    octv3 = 12

    for x in range(16):
        for z in range(16):
            xx = (x + x_offset) / 16 / freq
            zz = (z + z_offset) / 16 / freq

            e = (
                (noise.noise2(octv1 * xx, octv1 * zz) + 1) / 2 / octv1
                + (noise.noise2(octv2 * xx, octv2 * zz) + 1) / 2 / octv2
                + (noise.noise2(octv3 * xx, octv3 * zz) + 1) / 2 / octv3
            )

            e /= octv1 + octv2 + octv3

            height_map[x][z] = math.pow(e, .5)

    # print(min(height_map.flatten().tolist())*256, max(height_map.flatten().tolist())*256)

    ebl1 = (palette["bedrock"], palette["stone"])
    ebl2 = (palette["bedrock"], palette["stone"], palette["dirt"])

    for y in range(32):
        for x in range(16):
            for z in range(16):
                y2 = int(height_map[x][z] * 256)

                y2_y_16 = y2 - y - 16

                if y2_y_16 > 0 and chunk[y2_y_16][z][x] != palette["bedrock"]:
                    chunk[y2_y_16, z, x] = palette["stone"]

                y2_y_12 = y2 - y - 12

                if y2_y_12 > 0 and chunk[y2_y_12][z][x] not in ebl1:
                    chunk[y2_y_12, z, x] = palette["dirt"]

                y2_y_11 = y2 - y - 11

                if y2_y_11 > 0 and chunk[y2_y_11][z][x] not in ebl2:
                    chunk[y2_y_11, z, x] = palette["grass"]

                if 11 > y > 5 and chunk[y][z][x] == palette["grass"]:
                    chunk[y][z][x] = palette["water"]

    for y in range(5, 11):
        for x in range(16):
            for z in range(16):
                if chunk[y-1, z, x] == palette["water"] and chunk[y][z][x] == palette["air"]:
                    chunk[y][z][x] = palette["water"]

    return chunk.tolist()


def dump_to_obj(file, chunks: dict) -> None:
    points = {}
    rpoints = {}
    faces = {}
    rfaces = {}

    def append_point(*p) -> None:
        if not rpoints.get(p):
            points[len(points) - 1] = p
            rpoints[p] = len(points) - 1

    def append_face(f) -> None:
        if not rfaces.get(f):
            faces[len(faces) - 1] = f
            rfaces[f] = len(faces) - 1

    for cx, cz in chunks.keys():
        chunk = chunks[cx, cz]

        cxo = cx * 16
        czo = cz * 16

        for y in range(256):
            for z in range(16):
                for x in range(16):
                    if chunk[y][z][x] == 0:  # air
                        continue

                    tx = x + cxo
                    tz = z + czo

                    append_point(tx, y, tz)
                    append_point(tx + 1, y, tz)
                    append_point(tx, y + 1, tz)
                    append_point(tx, y, tz + 1)
                    append_point(tx + 1, y + 1, tz)
                    append_point(tx, y + 1, tz + 1)
                    append_point(tx + 1, y, tz + 1)
                    append_point(tx + 1, y + 1, tz + 1)

    for cx, cz in chunks.keys():
        chunk = chunks[cx, cz]

        cxo = cx * 16
        czo = cz * 16

        maxes = {}

        for y in range(256):
            for z in range(16):
                for x in range(16):
                    if chunk[y][z][x] != 0 and y > maxes.get((z, x), -1):
                        maxes[z, x] = y

        for y in range(256):
            for z in range(16):
                prim_cond = y == 0 or z == 0 or z == 15

                for x in range(16):
                    if prim_cond or maxes[z, x] == y or x == 0 or x == 15:
                        block = chunk[y][z][x]

                        if block == 0:  # air
                            continue

                        block = palette[block]

                        tx = x + cxo
                        tz = z + czo

                        i1 = rpoints[(tx, y, tz)] + 1
                        i2 = rpoints[(tx + 1, y, tz)] + 1
                        i3 = rpoints[(tx, y + 1, tz)] + 1
                        i4 = rpoints[(tx, y, tz + 1)] + 1
                        i5 = rpoints[(tx + 1, y + 1, tz)] + 1
                        i6 = rpoints[(tx, y + 1, tz + 1)] + 1
                        i7 = rpoints[(tx + 1, y, tz + 1)] + 1
                        i8 = rpoints[(tx + 1, y + 1, tz + 1)] + 1

                        append_face(f"usemtl {block}\nf {i1} {i2} {i7} {i4}")
                        append_face(f"f {i1} {i2} {i5} {i3}")
                        append_face(f"f {i4} {i7} {i8} {i6}")
                        append_face(f"f {i1} {i4} {i6} {i3}")
                        append_face(f"f {i2} {i5} {i8} {i7}")
                        append_face(f"f {i3} {i5} {i8} {i6}")

    file.write("\n".join([f"v {p[0]} {p[1]} {p[2]}" for p in points.values()]) + "\n" + "\n".join(faces.values()))


with open("test.obj", "w+") as f:
    noise = SimplexNoise()
    chunks = {}

    radius = 1 if len(sys.argv) < 2 else int(sys.argv[1])

    print("Generating chunks...")
    start = pf()

    for x in range(-radius, radius):
        for z in range(-radius, radius):
            chunks[x, z] = noisy_chunk(noise, x, z)

    print(f"Done generating chunks. ({(pf() - start):02.02f} seconds for {len(chunks)} chunks)")

    print("Dumping to obj file...")
    start = pf()

    dump_to_obj(f, chunks)
    print(f"Done dumping. ({(pf() - start):02.02f} seconds for {len(chunks)} chunks)")
