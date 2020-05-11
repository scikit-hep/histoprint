==========
histoprint
==========

Pretty print Numpy histograms to the console

How does it work?
-----------------

Histoprint uses a mix of terminal color codes and unicode trickery (i.e.
combining characters) to plot overlaying histograms.

Examples
--------

Some examples::

    A = np.random.randn(1000) - 2
    B = np.random.randn(1000)
    C = np.random.randn(1000) + 2
    D = np.random.randn(500) * 2

    # text_hist is a thin wrapper for numpy.histogram
    text_hist(
        B, bins=[-5, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 5], title="Variable bin widths"
    )

    histA = np.histogram(A, bins=15, range=(-5, 5))
    histB = np.histogram(B, bins=15, range=(-5, 5))
    histC = np.histogram(C, bins=15, range=(-5, 5))
    histD = np.histogram(D, bins=15, range=(-5, 5))
    histAll = ([histA[0], histB[0], histC[0], histD[0]], histA[1])

    # print_hist can be used to print multiple histograms at once
    # (or just to print a single one as returned by numpy.histogram)
    print_hist(histAll, title="Overlays", labels="ABCDE")
    print_hist(
        histAll,
        title="Stacks",
        stack=True,
        symbols="      ",
        bg_colors="rgbcmy",
        labels="ABCDE",
    )
    print_hist(
        histAll,
        title="Summaries",
        symbols=r"=|\/",
        fg_colors="0",
        bg_colors="0",
        labels=["AAAAAAAAAAAAAAAA", "B", "CCCCCCCCCCCCC", "D"],
        summary=True,
    )

.. image:: examples.png

The last example does not use terminal colors, so it can be copied as text::

                                       Summaries
    -5.00e+00 _
    -4.33e+00 _═⃫
    -3.67e+00 _═⃫═⃫═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏
    -3.00e+00 _═⃫═⃫═⃫═⃫═⃫═⃫═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏
    -2.33e+00 _╪⃫╪⃫═⃫═⃫═⃫═⃫═⃫═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏
    -1.67e+00 _╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫═⃫═⃫═⃫═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏
    -1.00e+00 _╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏═͏
    -3.33e-01 _╪⃥⃫╪⃥⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪⃫╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏╪͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏
     3.33e-01 _╪⃥⃫╪⃥⃫╪⃥⃫╪⃥⃫╪⃥⃫╪⃥⃫╪⃫╪⃫╪⃫╪⃫│⃫│⃫│⃫│⃫│⃫│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏
     1.00e+00 _╪⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏│͏
     1.67e+00 _│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥│⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥
     2.33e+00 _│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥⃫│⃥│⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥
     3.00e+00 _│⃥⃫│⃥⃫ ⃥⃫ ⃥⃫ ⃥⃫ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥
     3.67e+00 _ ⃥⃫ ⃥⃫ ⃥⃫ ⃥⃫ ⃥⃫ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥
     4.33e+00 _ ⃥⃫ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥ ⃥
     5.00e+00 _ ⃥⃫ ⃥
                 ═͏ AAAAAAAAAAAAAAAA │͏ B          ⃥ CCCCCCCCCCCCC  ⃫ D
           Sum:  9.99e+02           1.00e+03    9.99e+02        4.92e+02
           Avg: -1.98e+00           1.13e-02    1.99e+00       -1.71e-01
           Std:  1.03e+00           1.03e+00    9.94e-01        2.00e+00
