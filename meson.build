project('bpf_cc', 'c')

clang = find_program('clang')

bpf_source = files('bpf/bpf_cc.c')

bpf_o = custom_target('bpf_cc.o',
    input: 'bpf/bpf_cc.c',
    output: 'bpf_cc.o',
    command: [clang, '-g', '-O2', '-target', 'bpf', '-c', '@INPUT@', '-o' , '@OUTPUT@']
)
