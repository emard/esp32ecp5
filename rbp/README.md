# FFM/RBP board programmer

artix7.py: can use bscan bitstream (jtag-spi passthru) for xc3sprog
[bscan7.bit source](https://github.com/f32c/f32c/tree/master/rtl/proj/xilinx/ffm-a7100/ffm_a7100_jtag_spi_bridge)

cyclone5.py: prog() probably needs *.rbf (raw binary file):
but bitstream never started properly so it is not yet
sure is rbf correct format

    quartus_cpf -c -o bitstream_compression=on my_input_file.sof my_output_file.rbf
