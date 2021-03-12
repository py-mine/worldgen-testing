from opensimplex import OpenSimplex  # pip install opensimplex
from time import perf_counter as pf
from random import Random
import numpy
import math
import sys

HEIGHT_FACTOR = 72


# here, a "chunk" refers to a 256x16x16 array of block states

palette = {"air": 0, "bedrock": 1, "stone": 2, "dirt": 3, "grass": 4, "water": 5}

palette = {**palette, **{v: k for k, v in palette.items()}}


def blank_chunk() -> list:  # used to test dumping to a obj file
    #                       y   z   x
    chunk = numpy.zeros((256, 16, 16), numpy.uint64)  # kinda how chunks are stored in pymine

    chunk[0:5] = palette["bedrock"]
    chunk[5:69] = palette["stone"]
    chunk[69:73] = palette["dirt"]
    chunk[73:74] = palette["grass"]

    return chunk.tolist()


def map_range(x: int, in_min: int, in_max: int, out_min: int, out_max: int) -> float:
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def distance(y1: int, z1: int, x1: int, y2: int, z2: int, x2: int) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2)


def remove_sphere(chunks: dict, y: int, z: int, x: int, radius: int) -> None:
    for y2 in range(y - radius, y + radius):
        for z2 in range(z - radius, z + radius):
            for x2 in range(x - radius, x + radius):
                d = distance(y, z, x, y2, z2, x2)

                if d < radius:
                    cx = math.floor(x2 / 16)
                    cz = math.floor(z2 / 16)

                    try:
                        if chunks[cx, cz][y2][z2 % 16][x2 % 16] == 4:
                            chunks[cx, cz][y2][z2 % 16][x2 % 16] = 0  # air
                    except KeyError:
                        pass
    return chunks


def noisy_chunk(noise, randomness, chunk_x: int, chunk_z: int) -> list:
    chunk = [[[0] * 16 for _ in range(16)] for _ in range(256)]
    height_map = [[0] * 16 for _ in range(16)]

    x_offset = 16 * chunk_x
    z_offset = 16 * chunk_z

    for y in range(5):
        for x in range(16):
            for z in range(16):
                n = noise.noise3d(x, y, z)

                # I do this to get more of a gradient between the different layers of bedrock
                if y < 3 and n >= 0:
                    chunk[y + 1][z][x] = palette["bedrock"]
                elif n > 0:
                    chunk[y + 1][z][x] = palette["bedrock"]

    frequency = 20
    octaves = [3, 7, 12]
    height_factor = HEIGHT_FACTOR  # how high the surface is
    # redistrib = 0.035 * (256 / height_factor)
    redistrib = 0.05 * (256 / height_factor)

    octave_inverted_sum = sum([1 / o for o in octaves])

    for z in range(16):
        for x in range(16):
            nx = (x + x_offset) / 16 / frequency
            nz = (z + z_offset) / 16 / frequency

            # octaves
            e = sum([(noise.noise2d(o * nx, o * nz) / o) for o in octaves])
            e /= octave_inverted_sum

            # account for noise2d() range (-1 to 1)
            e += 1
            e /= 2

            # redistribution
            e **= redistrib

            # world is 256 blocks high but fuck it
            e *= height_factor

            # block coords can't be floats
            e = int(e)

            for y in range(e):
                if y < (height_factor - 14):  # draw grass or water depending on height
                    chunk[y + 9][z][x] = palette["water"]
                else:
                    chunk[y + 9][z][x] = palette["grass"]

                for i in range(9):  # draw dirt
                    chunk[y + i][z][x] = palette["dirt"]

                chunk[y][z][x] = palette["stone"]  # draw stone

    # generate the bedrock layers
    for y in range(5):
        for z in range(16):
            for x in range(16):
                if y == 0:
                    chunk[y][z][x] = palette["bedrock"]
                else:
                    n = noise.noise3d(x + x_offset, y, z + z_offset)

                    # I do this to get more of a gradient between the different layers of bedrock
                    if y < 2 and n >= 0:
                        chunk[y][z][x] = palette["bedrock"]
                    elif n > 0:
                        chunk[y][z][x] = palette["bedrock"]

    return chunk


def wormy_bois(chunks, randomness, noise):
    segment_len = 3
    segments = 25
    worms = []

    for cx, cz in chunks.keys():
        chunk = chunks[cx, cz]

        x_offset = cx * 16
        z_offset = cz * 16

        for y in range(5, HEIGHT_FACTOR):
            for z in range(16):
                z_zo = z + z_offset

                for x in range(16):
                    x_xo = x + x_offset

                    if noise.noise3d(x_xo, y, z_zo) > 0.875:
                        worms.append((x_xo, y, z_zo))

        # if noise.noise2d(x_offset*4, z_offset*4) > 0.875:
        #     max = (0, 0, 0, 0)
        #     for y in range(5, 128):
        #         for z in range(16):
        #             for x in range(16):
        #                 n = noise.noise3d(x+x_offset, y, z+z_offset)
        #                 if n > max[3]:
        #                     max = (x, y, z, n)
        #     worms += [(max[0]+x_offset, max[1], max[2]+z_offset)]

    for x, y, z in worms:
        for s in range(segments):
            noise_a = noise.noise3d(x, y, z)
            noise_b = noise.noise3d(x * x, y * y, z * z)

            pitch = map_range(noise_a, -1, 1, -360, 360)
            yaw = map_range(noise_b, -1, 1, -360, 360)

            cos_pitch = math.cos(pitch)

            yi = math.sin(yaw) * cos_pitch
            zi = math.sin(pitch)
            xi = math.cos(yaw) * cos_pitch

            for p in range(segment_len):
                remove_sphere(chunks, int(y), int(z), int(x), 4)

                y += yi
                z += zi
                x += xi

    return chunks, len(worms)


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

        # maxes = {}
        #
        # for y in range(256):
        #     for z in range(16):
        #         for x in range(16):
        #             if chunk[y][z][x] != 0 and y > maxes.get((z, x), -1):
        #                 maxes[z, x] = y

        for y in range(256):
            for z in range(16):
                for x in range(16):
                    block = chunk[y][z][x]

                    if chunk[y][z][x] == 0:  # air
                        continue

                    visible = False

                    if z == 0 or x == 0:
                        visible = True
                    else:
                        for y2 in (y - 1, y + 1):
                            for z2 in (z - 1, z + 1):
                                for x2 in (x - 1, x + 1):
                                    try:
                                        if chunk[y2][z2][x2] == 0:
                                            visible = True
                                            break
                                    except IndexError:
                                        visible = True
                                        break

                    if not visible:
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

    file.write("\n".join([f"v {p[0]} {p[1]} {p[2]}" for p in points.values()]) + "\n" + "\n".join(faces.values()) + "\n")


with open("test.obj", "w+") as f:
    seed = 1281134870109837483
    randomness = Random(seed)
    noise = OpenSimplex(seed=seed)
    chunks = {}

    radius = 1 if len(sys.argv) < 2 else int(sys.argv[1])

    print(f"Generating {(radius*2)**2} chunks...")
    start = pf()

    for x in range(-radius, radius):
        for z in range(-radius, radius):
            chunks[x, z] = noisy_chunk(noise, randomness, x, z)

    print(f"Done generating chunks. ({(pf() - start):02.02f} seconds for {len(chunks)} chunks)")

    print("Activating wormy bois...")
    start = pf()

    chunks, n = wormy_bois(chunks, randomness, noise)

    print(f"Wormy bois finished. ({(pf() - start):02.02f} seconds for {n} wormy bois)")

    print("Dumping to obj file...")
    start = pf()

    dump_to_obj(f, chunks)
    print(f"Done dumping. ({(pf() - start):02.02f} seconds for {len(chunks)} chunks)")
