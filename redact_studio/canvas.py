from dataclasses import replace
from PIL.ImageQt import ImageQt
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPixmap, QPainterPath, QPen, QColor, QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem
from .core import Shape


def pixmap(image):
    return QPixmap.fromImage(ImageQt(image))

class Canvas(QGraphicsView):
    changed = Signal()
    zoomed = Signal()

    def __init__(self, document):
        super().__init__()
        self.document = document
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.base_pixmap = pixmap(document.pixels)
        self.setScene(QGraphicsScene(self))
        self.tool = 'rect'
        self.color = '#000000'
        self.brush = 24
        self.items_by_index = []
        self.start = None
        self.points = []
        self.resize_index = None
        self.space = False
        self.panning = None
        self.setFocusPolicy(Qt.StrongFocus)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setBackgroundBrush(QColor('#181c25'))
        self.rebuild()

    def rebuild(self, selected=()):
        self.scene().clear()
        self.scene().addPixmap(self.base_pixmap)
        self.scene().setSceneRect(QRectF(0, 0, *self.document.pixels.size))
        self.items_by_index = []
        for i, shape in enumerate(self.document.shapes):
            if shape.kind == 'rect':
                x0,y0,x1,y1 = shape.bounds
                item = self.scene().addRect(QRectF(x0,y0,x1-x0,y1-y0), QPen(Qt.NoPen), QColor(shape.color))
            else:
                path = QPainterPath(QPointF(*shape.points[0]))
                for point in shape.points[1:]:
                    path.lineTo(QPointF(*point))
                if len(shape.points) == 1:
                    path.lineTo(QPointF(shape.points[0][0]+0.01, shape.points[0][1]))
                item = self.scene().addPath(path, QPen(QColor(shape.color), shape.width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            item.setData(0, i)
            item.setFlag(QGraphicsItem.ItemIsSelectable, True)
            item.setFlag(QGraphicsItem.ItemIsMovable, self.tool == 'select')
            item.setSelected(i in selected)
            self.items_by_index.append(item)
        self.changed.emit()

    def selected(self):
        return [i for i,item in enumerate(self.items_by_index) if item.isSelected()]

    def set_tool(self, tool):
        self.cancel()
        self.tool = tool
        self.setDragMode(QGraphicsView.RubberBandDrag if tool == 'select' else QGraphicsView.NoDrag)
        self.setCursor(Qt.OpenHandCursor if tool == 'pan' else Qt.CrossCursor)
        for item in self.items_by_index:
            item.setFlag(QGraphicsItem.ItemIsMovable, tool == 'select')
        self.changed.emit()

    def point(self, position):
        p = self.mapToScene(position)
        w,h = self.document.pixels.size
        return max(0,min(w,p.x())), max(0,min(h,p.y()))

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and (self.tool == 'pan' or self.space)):
            self.panning = event.position().toPoint()
            return
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        if self.tool in ('rect','brush'):
            self.start = self.point(event.position().toPoint())
            self.points = [self.start]
            self.draft = None
            return
        if self.tool == 'remove':
            item = self.itemAt(event.position().toPoint())
            if item in self.items_by_index:
                index = self.items_by_index.index(item)
                self.document.commit([s for i,s in enumerate(self.document.shapes) if i != index])
                self.rebuild()
            return
        if self.tool == 'select':
            point = self.mapToScene(event.position().toPoint())
            for i in self.selected():
                shape = self.document.shapes[i]
                if shape.kind == 'rect':
                    x0,y0,x1,y1 = shape.bounds
                    if (point-QPointF(x1,y1)).manhattanLength()*self.transform().m11() < 14:
                        self.resize_index = i
                        self.start = (x0,y0)
                        return
        super().mousePressEvent(event)
        self.changed.emit()

    def mouseMoveEvent(self, event):
        if self.panning is not None:
            now = event.position().toPoint()
            delta = now-self.panning
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value()-delta.y())
            self.panning = now
            return
        if self.start is not None:
            point = self.point(event.position().toPoint())
            if self.resize_index is not None:
                x,y = self.start
                self.items_by_index[self.resize_index].setRect(QRectF(QPointF(x,y), QPointF(*point)).normalized())
            else:
                self.points.append(point)
                if self.draft is not None:
                    self.scene().removeItem(self.draft)
                if self.tool == 'rect':
                    self.draft = self.scene().addRect(QRectF(QPointF(*self.start), QPointF(*point)).normalized(), QPen(Qt.NoPen), QColor(self.color))
                else:
                    path = QPainterPath(QPointF(*self.start))
                    for p in self.points[1:]: path.lineTo(QPointF(*p))
                    self.draft = self.scene().addPath(path,QPen(QColor(self.color),self.brush,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.panning is not None:
            self.panning = None
            return
        if self.start is not None:
            point = self.point(event.position().toPoint())
            if self.resize_index is not None:
                shapes = list(self.document.shapes)
                shapes[self.resize_index] = replace(shapes[self.resize_index], points=(self.start,point))
                self.document.commit(shapes)
            elif self.tool == 'brush' or (abs(point[0]-self.start[0]) >= 1 and abs(point[1]-self.start[1]) >= 1):
                points = tuple(self.points+[point]) if self.tool == 'brush' else (self.start,point)
                self.document.commit(self.document.shapes+[Shape(self.tool,points,self.color,self.brush)])
            self.start = None
            self.resize_index = None
            self.rebuild()
            return
        super().mouseReleaseEvent(event)
        if self.tool == 'select':
            selected = self.selected()
            shapes = list(self.document.shapes)
            for i,item in enumerate(self.items_by_index):
                if not item.pos().isNull():
                    shapes[i] = shapes[i].moved(item.pos().x(), item.pos().y())
            self.document.commit(shapes)
            self.rebuild(selected)

    def cancel(self):
        self.start = None
        self.resize_index = None
        self.panning = None
        self.rebuild(self.selected())

    def keyPressEvent(self,event):
        if event.key() == Qt.Key_Space:
            self.space = True
            event.accept()
        elif event.key() == Qt.Key_Escape:
            self.cancel()
        else: super().keyPressEvent(event)

    def keyReleaseEvent(self,event):
        if event.key() == Qt.Key_Space:
            self.space = False
        else: super().keyReleaseEvent(event)

    def wheelEvent(self,event):
        self.zoom(1.2 if event.angleDelta().y()>0 else 1/1.2, event.position().toPoint())

    def zoom(self, factor, anchor=None):
        anchor = anchor or self.viewport().rect().center()
        before = self.mapToScene(anchor)
        old = self.transform().m11()
        target = max(0.1,min(8,old*factor))
        self.scale(target/old,target/old)
        delta = self.mapToScene(anchor)-before
        self.translate(delta.x(),delta.y())
        self.zoomed.emit()

    def fit(self):
        self.fitInView(self.sceneRect(),Qt.KeepAspectRatio)
        scale = self.transform().m11()
        if scale < .1: self.scale(.1/scale,.1/scale)
        if scale > 8: self.scale(8/scale,8/scale)
        self.zoomed.emit()
