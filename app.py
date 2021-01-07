import streamlit as st
import pandas as pd
import numpy as np
import glob
import os
from plotnine import *

###################################################################



###################################################################

def main():
    """main app"""

    st.write("# SRFA Control - Calibration tests")

    st.sidebar.write("### 1 - Select 3 `.d` files :")


    ## Display summary mf search
    st.write("### Summary Molecular Formula Search")



    ## Error distribution plot
    st.write("### Error distribution")

    ## scatter plot m/z vs Error
    # st.pyplot(p.draw())





if __name__ == "__main__":
    main()
