from noise import pnoise1 as perlin  # pip install noise
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
    chunk = numpy.ndarray((16, 256, 16), numpy.uint32)  # kinda how chunks are stored in pymine
    chunk.fill(0)

    chunk[0:5] = palette["bedrock"]
    chunk[5:69] = palette["stone"]
    chunk[69:73] = palette["dirt"]
    chunk[73:74] = palette["grass"]

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
                i = (y + 1) * (z + 1) * (x + 1)

                if i % 32 == 0:
                    print(f"{i:05.0f}/{total_len} (1/2)\r", end="")

                if chunk[x, y, z] == 0:
                    continue

                append_point(x, y, z)
                append_point(x + 1, y, z)
                append_point(x, y + 1, z)
                append_point(x, y, z + 1)
                append_point(x + 1, y + 1, z)
                append_point(x, y + 1, z + 1)
                append_point(x + 1, y, z + 1)
                append_point(x + 1, y + 1, z + 1)

    print()

    for y in range(256):
        for z in range(16):
            for x in range(16):
                i = (y + 1) * (z + 1) * (x + 1)

                if i % 32 == 0:
                    print(f"{i:05.0f}/{total_len} (2/2)\r", end="")

                if chunk[x, y, z] == 0:
                    continue

                i1 = rpoints.get((x, y, z)) + 1
                i2 = rpoints.get((x + 1, y, z)) + 1
                i3 = rpoints.get((x, y + 1, z)) + 1
                i4 = rpoints.get((x, y, z + 1)) + 1
                i5 = rpoints.get((x + 1, y + 1, z)) + 1
                i6 = rpoints.get((x, y + 1, z + 1)) + 1
                i7 = rpoints.get((x + 1, y, z + 1)) + 1
                i8 = rpoints.get((x + 1, y + 1, z + 1)) + 1

                append_face(f"f {i1} {i2} {i7} {i4}")
                append_face(f"f {i1} {i2} {i5} {i3}")
                append_face(f"f {i4} {i7} {i8} {i6}")
                append_face(f"f {i1} {i4} {i6} {i3}")
                append_face(f"f {i2} {i5} {i8} {i7}")
                append_face(f"f {i3} {i5} {i8} {i6}")

    print()

    file.write("\n".join([f"v {p[0]} {p[1]} {p[2]}" for p in points.values()]) + "\n" + "\n".join(faces.values()))


chunk = blank_chunk()

with open("test.obj", "w+") as f:
    dump_to_obj(f, chunk)
