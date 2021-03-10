from noise.perlin import SimplexNoise  # pip install noise
import numpy
import math


# here, a "chunk" refers to a 16x256x16 array of block states

palette = {
    "air": 0,
    "bedrock": 1,
    "stone": 2,
    "dirt": 3,
    "grass": 4,
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

    return chunk


def noisy_chunk(noise, chunk_x: int, chunk_z: int) -> numpy.ndarray:
    chunk = numpy.zeros((256, 16, 16), numpy.uint64)
    chunk[0] = palette["bedrock"]
    height_map = numpy.zeros((16, 16), numpy.float32)

    x_offset = 16 * chunk_x
    z_offset = 16 * chunk_z

    for x in range(16):
        for z in range(16):
            xx = (x + x_offset) / 16
            zz = (z + z_offset) / 16

            e = (
                (noise.noise2(0.5 * xx, 0.5 * zz) + 1) / 2
                + (noise.noise2(0.25 * xx, 0.25 * zz) + 1) / 2
                + (noise.noise2(0.125 * xx, 0.125 * zz) + 1) / 2
            )

            e /= 0.5 + 0.25 + 0.125

            height_map[x, z] = math.pow(e, 0.15)

    for y in range(16):
        for x in range(16):
            for z in range(16):
                y2 = int(height_map[x, z] * 64)
                chunk[y2 - y, z, x] = palette["stone"]

    return chunk


def dump_to_obj(file, chunks: dict) -> None:
    # amount = len(chunks)
    # joined_chunks = numpy.zeros((256, 16 * amount, 16 * amount))
    #
    # for cxz, chunk in chunks.items():
    #     cx, cz = cxz
    #
    #     cx *= -len(chunks) // 2
    #     cz *= -len(chunks) // 2
    #
    #     # print(cz*16, cz*16+16)
    #     # print(cx*16, cx*16+16)
    #     print(cz, cx)
    #
    #     joined_chunks[..., cx*16:cx*16+16, cz*16:cz*16+16,] = chunk

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
        for y in range(256):
            for z in range(16):
                for x in range(16):
                    if chunks[cx, cz][y, z, x] == 0:  # air
                        continue

                    tx = x + cx * 16
                    tz = z + cz * 16

                    append_point(tx, y, tz)
                    append_point(tx + 1, y, tz)
                    append_point(tx, y + 1, tz)
                    append_point(tx, y, tz + 1)
                    append_point(tx + 1, y + 1, tz)
                    append_point(tx, y + 1, tz + 1)
                    append_point(tx + 1, y, tz + 1)
                    append_point(tx + 1, y + 1, tz + 1)

    for cx, cz in chunks.keys():
        for y in range(256):
            for z in range(16):
                for x in range(16):
                    block = chunks[cx, cz][y, z, x]

                    if block == 0:  # air
                        continue

                    block = palette[block]

                    tx = x + cx * 16
                    tz = z + cz * 16

                    i1 = rpoints.get((tx, y, tz)) + 1
                    i2 = rpoints.get((tx + 1, y, tz)) + 1
                    i3 = rpoints.get((tx, y + 1, tz)) + 1
                    i4 = rpoints.get((tx, y, tz + 1)) + 1
                    i5 = rpoints.get((tx + 1, y + 1, tz)) + 1
                    i6 = rpoints.get((tx, y + 1, tz + 1)) + 1
                    i7 = rpoints.get((tx + 1, y, tz + 1)) + 1
                    i8 = rpoints.get((tx + 1, y + 1, tz + 1)) + 1

                    append_face(f"usemtl {block}\nf {i1} {i2} {i7} {i4}")
                    append_face(f"usemtl {block}\nf {i1} {i2} {i5} {i3}")
                    append_face(f"usemtl {block}\nf {i4} {i7} {i8} {i6}")
                    append_face(f"usemtl {block}\nf {i1} {i4} {i6} {i3}")
                    append_face(f"usemtl {block}\nf {i2} {i5} {i8} {i7}")
                    append_face(f"usemtl {block}\nf {i3} {i5} {i8} {i6}")

    file.write("\n".join([f"v {p[0]} {p[1]} {p[2]}" for p in points.values()]) + "\n" + "\n".join(faces.values()))


with open("test.obj", "w+") as f:
    noise = SimplexNoise()
    chunks = {}

    radius = 3

    for x in range(-radius, radius):
        for z in range(-radius, radius):
            chunks[x, z] = noisy_chunk(noise, x, z)

    dump_to_obj(f, chunks)
