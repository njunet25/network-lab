#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

#define TCP_CONG_NON_RESTRICTED 0x1

char __license[] SEC("license") = "GPL";
const char name[] = "bpf_cc";

SEC("struct_ops")
void BPF_PROG(init, struct sock *sk) {

}

SEC("struct_ops")
void BPF_PROG(release, struct sock *sk) {

}

SEC("struct_ops")
__u32 BPF_PROG(ssthresh, struct sock *sk) {
   return 1024;
}

SEC("struct_ops")
void BPF_PROG(cong_avoid, struct sock *sk, __u32 ack, __u32 acked) {

}

SEC("struct_ops")
__u32 BPF_PROG(undo_cwnd, struct sock *sk) {
   return 512;
}

SEC(".struct_ops")
struct tcp_congestion_ops bpf_cc = {
   .name = "bpf_cc", 
   .flags = TCP_CONG_NON_RESTRICTED,
   .ssthresh = (void *)ssthresh,
   .cong_avoid = (void *)cong_avoid,
   .undo_cwnd = (void *)undo_cwnd,
   .init = (void *)init,
   .release = (void *)release,
};