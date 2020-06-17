"""
I just like to write my own math modules.
This matrix is row-major. This fact will effect whether you multiply right or left.
"""

import math

import mathutils


class Matrix4f:

    def __init__(self) -> None:
        super().__init__()
        self.m00, self.m01, self.m02, self.m03 = 1.0, 0.0, 0.0, 0.0
        self.m10, self.m11, self.m12, self.m13 = 0.0, 1.0, 0.0, 0.0
        self.m20, self.m21, self.m22, self.m23 = 0.0, 0.0, 1.0, 0.0
        self.m30, self.m31, self.m32, self.m33 = 0.0, 0.0, 0.0, 1.0

    def getDataAsFloatArray(self):
        return [
            self.m00, self.m01, self.m02, self.m03,
            self.m10, self.m11, self.m12, self.m13,
            self.m20, self.m21, self.m22, self.m23,
            self.m30, self.m31, self.m32, self.m33]

    @staticmethod
    def createTranslation(xyz: tuple):
        m = Matrix4f()
        m.m03, m.m13, m.m23 = xyz
        return m

    @staticmethod
    def create_scale(xyz: tuple):
        m = Matrix4f()
        m.m00, m.m11, m.m22 = xyz
        return m

    @staticmethod
    def create_rotation_x(radians: float):
        m = Matrix4f()
        c = math.cos(radians)
        s = math.sin(radians)
        m.m11, m.m12, m.m21, m.m22 = c, -s, s, c

        return m

    @staticmethod
    def create_rotation_y(radians: float):
        m = Matrix4f()
        c = math.cos(radians)
        s = math.sin(radians)
        m.m00, m.m02, m.m20, m.m22 = c, s, -s, c
        return m

    @staticmethod
    def create_rotation_z(radians: float):
        m = Matrix4f()
        c = math.cos(radians)
        s = math.sin(radians)
        m.m00, m.m01, m.m10, m.m11 = c, -s, s, c
        return m

    @staticmethod
    def multiply(left, right):
        m = Matrix4f()
        m.m00 = left.m00 * right.m00 + left.m01 * right.m10 + left.m02 * right.m20 + left.m03 * right.m30
        m.m01 = left.m00 * right.m01 + left.m01 * right.m11 + left.m02 * right.m21 + left.m03 * right.m31
        m.m02 = left.m00 * right.m02 + left.m01 * right.m12 + left.m02 * right.m22 + left.m03 * right.m32
        m.m03 = left.m00 * right.m03 + left.m01 * right.m13 + left.m02 * right.m23 + left.m03 * right.m33
        m.m10 = left.m10 * right.m00 + left.m11 * right.m10 + left.m12 * right.m20 + left.m13 * right.m30
        m.m11 = left.m10 * right.m01 + left.m11 * right.m11 + left.m12 * right.m21 + left.m13 * right.m31
        m.m12 = left.m10 * right.m02 + left.m11 * right.m12 + left.m12 * right.m22 + left.m13 * right.m32
        m.m13 = left.m10 * right.m03 + left.m11 * right.m13 + left.m12 * right.m23 + left.m13 * right.m33
        m.m20 = left.m20 * right.m00 + left.m21 * right.m10 + left.m22 * right.m20 + left.m23 * right.m30
        m.m21 = left.m20 * right.m01 + left.m21 * right.m11 + left.m22 * right.m21 + left.m23 * right.m31
        m.m22 = left.m20 * right.m02 + left.m21 * right.m12 + left.m22 * right.m22 + left.m23 * right.m32
        m.m23 = left.m20 * right.m03 + left.m21 * right.m13 + left.m22 * right.m23 + left.m23 * right.m33
        m.m30 = left.m30 * right.m00 + left.m31 * right.m10 + left.m32 * right.m20 + left.m33 * right.m30
        m.m31 = left.m30 * right.m01 + left.m31 * right.m11 + left.m32 * right.m21 + left.m33 * right.m31
        m.m32 = left.m30 * right.m02 + left.m31 * right.m12 + left.m32 * right.m22 + left.m33 * right.m32
        m.m33 = left.m30 * right.m03 + left.m31 * right.m13 + left.m32 * right.m23 + left.m33 * right.m33
        return m

    def multiply_right(self, right):
        return self.multiply(self, right)

    def multiply_left(self, left):
        return self.multiply(left, self)

    def transform(self, *v):
        return (v[0] * self.m00 + v[1] * self.m01 + v[2] * self.m02 + self.m03,
                v[0] * self.m10 + v[1] * self.m11 + v[2] * self.m12 + self.m13,
                v[0] * self.m20 + v[1] * self.m21 + v[2] * self.m22 + self.m23)

    def toBlenderMatrix(self):
        return mathutils.Matrix((
            (self.m00, self.m01, self.m02, self.m03),
            (self.m10, self.m11, self.m12, self.m13),
            (self.m20, self.m21, self.m22, self.m23),
            (self.m30, self.m31, self.m32, self.m33)
        ))
