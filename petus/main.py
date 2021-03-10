from noise.perlin import SimplexNoise # pip install noise
import numpy


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


def noisy_chunk() -> numpy.ndarray:
    noise = SimplexNoise()
    chunk = numpy.zeros((256, 16, 16), numpy.uint64)

    chunk[0] = palette["bedrock"]

    for y in range(1, 256):
        for z in range(16):
            for x in range(16):
                elevation = (noise.noise3(256/(y+1)/5, 16/(z+1)/5, 16/(x+1)/5) + 1) * 128

                if elevation < 5:
                    chunk[y, z, x] = palette["bedrock"]
                elif elevation < 45:
                    chunk[y, z, x] = palette["stone"]
                elif elevation < 55:
                    chunk[y, z, x] = palette["dirt"]
                elif elevation < 56:
                    chunk[y, z, x] = palette["grass"]

    return chunk


def dump_to_obj(file, chunk: numpy.ndarray) -> None:
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

    total_len = len(chunk.flatten())

    for y in range(256):
        for z in range(16):
            for x in range(16):
                if chunk[y, z, x] == 0:  # air
                    continue

                append_point(x, y, z)
                append_point(x + 1, y, z)
                append_point(x, y + 1, z)
                append_point(x, y, z + 1)
                append_point(x + 1, y + 1, z)
                append_point(x, y + 1, z + 1)
                append_point(x + 1, y, z + 1)
                append_point(x + 1, y + 1, z + 1)

    for y in range(256):
        for z in range(16):
            for x in range(16):
                block = chunk[y, z, x]

                if block == 0:  # air
                    continue

                block = palette[block]

                i1 = rpoints.get((x, y, z)) + 1
                i2 = rpoints.get((x + 1, y, z)) + 1
                i3 = rpoints.get((x, y + 1, z)) + 1
                i4 = rpoints.get((x, y, z + 1)) + 1
                i5 = rpoints.get((x + 1, y + 1, z)) + 1
                i6 = rpoints.get((x, y + 1, z + 1)) + 1
                i7 = rpoints.get((x + 1, y, z + 1)) + 1
                i8 = rpoints.get((x + 1, y + 1, z + 1)) + 1

                append_face(f"usemtl {block}\nf {i1} {i2} {i7} {i4}")
                append_face(f"usemtl {block}\nf {i1} {i2} {i5} {i3}")
                append_face(f"usemtl {block}\nf {i4} {i7} {i8} {i6}")
                append_face(f"usemtl {block}\nf {i1} {i4} {i6} {i3}")
                append_face(f"usemtl {block}\nf {i2} {i5} {i8} {i7}")
                append_face(f"usemtl {block}\nf {i3} {i5} {i8} {i6}")

    file.write("\n".join([f"v {p[0]} {p[1]} {p[2]}" for p in points.values()]) + "\n" + "\n".join(faces.values()))


with open("test.obj", "w+") as f:
    chunk = noisy_chunk()
    dump_to_obj(f, chunk)
