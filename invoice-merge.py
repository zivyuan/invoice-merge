# -*- coding: utf-8 -*-

import sys
import re
import fitz
from os import path, walk, makedirs, rmdir, remove
import datetime
import cv2
import numpy as np
import shutil
from random import random
from math import ceil

def rmdirs(folder):
    folder = path.realpath(folder)
    if path.isdir(folder):
        for root, dirs, files in walk(folder):
            for file in files:
                fpath = path.join(root, file)
                remove(fpath)
            for f in dirs:
                fpath = path.join(root, f)
                rmdirs(fpath)
        rmdir(folder);
    else:
        remove(folder)


def convertPNG(pdfPath, imagePath):
    pdfDoc = fitz.open(pdfPath)
    basename = path.basename(pdfPath)
    print("convert ", basename)
    basename = basename[0:-4]

    for pg in range(pdfDoc.pageCount):
        page = pdfDoc[pg]
        rotate = int(0)
        # 每个尺寸的缩放系数为1.3，这将为我们生成分辨率提高2.6的图像。
        # 此处若是不做设置，默认图片大小为：792X612, dpi=96
        zoom_x = 4 #(1.33333333-->1056x816)   (2-->1584x1224)
        zoom_y = 4
        mat = fitz.Matrix(zoom_x, zoom_y).prerotate(rotate)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        if not path.exists(imagePath):#判断存放图片的文件夹是否存在
            makedirs(imagePath) # 若图片文件夹不存在就创建
        pix.save(imagePath+'/'+'%s-%s.png' % (basename, pg))#将图片写入指定的文件夹内


def copyImage(source, target):
    basename = path.basename(source)
    print('   copy ', basename)
    shutil.copyfile(source, target + '/' + basename)


def convertFolder(pdfFolder, target):
    startTime_pdf2img = datetime.datetime.now()#开始时间

    patPdf = re.compile(r'\.pdf$', re.I)
    patImg = re.compile(r'\.(png|jpeg|gif|jpg)$', re.I)
    total = 0

    print("PDF folder: ", pdfFolder);
    for root, dirs, files in walk(pdfFolder):
        for file in files:
            basename = path.basename(file)
            matches = re.search(patPdf, file)
            if matches is not None:
                pdf = path.realpath(path.join(root, file));
                convertPNG(pdf, target);
                total = total + 1
            matches = re.search(patImg, file)
            if matches is not None:
                img = path.realpath(path.join(root, file))
                copyImage(img, target)

    endTime_pdf2img = datetime.datetime.now()#结束时间
    print('Total convert ', total, ' invoce(s).')
    print('Cost ',(endTime_pdf2img - startTime_pdf2img).seconds, 'second(s)')


def mergePNG(folder, pdfName = None):
    fbase = path.basename(folder)
    if pdfName is None:
        pdfName = fbase
    workFolder = folder[0:-len(fbase)]
    tmpPage = folder[0:-len(fbase)] + 'mergeinvoice.png'
    output = workFolder + pdfName + '.pdf'
    pageWidth = 2480
    pageHeight = 3508
    invWidth = 2300
    invHeight = 1500
    pageHalfHeight = int(pageHeight / 2)

    pdfPages = []
    count = 0;
    pdf = fitz.open()
    img = None;
    for root, dirs, files in walk(folder):
        for file in files:
            filepath = path.join(root, file)
            if (count % 2) == 0:
                # A4 纸张像素尺寸, 300DPI
                img = np.zeros((pageHeight, pageWidth, 3), np.uint8)
                img.fill(255)
                pdfPages.append(img)

                invoice1 = cv2.imread(filepath)
                invoice1 = cv2.resize(invoice1, (invWidth, invHeight))
                img[127 : invHeight + 127, 90:invWidth + 90] = invoice1

            elif (count %2) == 1:
                invoice2 = cv2.imread(filepath)
                invoice2 = cv2.resize(invoice2, (invWidth, invHeight))
                img[127 + pageHalfHeight:invHeight + 127 + pageHalfHeight, 90:invWidth + 90] = invoice2

                cv2.imwrite(tmpPage, img)
                page = fitz.open(tmpPage)
                pdfPage = fitz.open("pdf", page.convert_to_pdf())
                pdf.insert_pdf(pdfPage)
                print("第 " + str(int(count / 2) + 1) + " 页PDF合并完成.")
            count += 1

    if (count % 2) == 1:
        cv2.imwrite(tmpPage, img)
        page = fitz.open(tmpPage)
        pdfPage = fitz.open("pdf", page.convert_to_pdf())
        pdf.insert_pdf(pdfPage)
        print("第 " + str(int(count / 2) + 1) + " 页PDF合并完成.")

    pdf.save(output)
    pdf.close()
    remove(tmpPage)
    print("总共合并 " + str(count) + " 张发票，生成 " + str(ceil(count / 2)) + " 页PDF.")
    print("\nPDF 文件名:   " + pdfName + '.pdf\n')


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('必须指定发票目录');
        exit();
    pp = sys.argv[1]
    pdfFolder = path.realpath(pp);
    if not path.exists(pdfFolder):
        print('发票目录不存在');
        exit();

    basename = path.basename(pdfFolder);
    tmpFolder = pdfFolder[0:(-len(basename)-1)] + '/' + basename + '.inv_assets'
    print("合并文件夹 " + basename +  " 里的发票");
    makedirs(tmpFolder)

    convertFolder(pdfFolder, tmpFolder);

    mergePNG(tmpFolder, basename)

    rmdirs(tmpFolder)

    print("发票合并完成! \n请查看与发票目录同名的PDF文件.");
