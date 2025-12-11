#include <arpa/inet.h>
#include <asm-generic/errno-base.h>
#include <netinet/in.h>
#include <netinet/ip_icmp.h>
#include <arpa/tftp.h>
#include <resolv.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/ucontext.h>
#include <unistd.h>
#include <stdlib.h>
#include <netdb.h>
#include <errno.h>

#include "libtftp.h"

/**
  @brief TFTP Reliable Transfer

  @param[in] sfd socket fd
  @param[out] fp file to write to.
  @param[in] window window size. windowsize extension will always be enabled for the lab.

  @return non-zero on success.
 */
int tftp_loop(int sfd, FILE *fp, short window) {
  // We don't know if this code is correct.

  int ret, acked = 0;
  size_t block_size = 512;
  char *buf = malloc(1024);
  char *block;
  int len;
  int retrys = 0;
  int extra_ack = 0;

  do  {
    ret = recv(sfd, buf, 1024, 0);
    if (ret < 0 && errno == EAGAIN) {
      if (++retrys > 10) {
        fprintf(stderr, "bailing out...\n");
        exit(1);
      }
      goto ack;
    } else if (ret < 0) {
      perror("recv");
      return 1;
    }
    retrys = 0;

    ret = tftp_parse_response(buf, ret, &block, &block_size);
    if (ret < 0) {
      fprintf(stderr, "unexpected error %d: %s\n", -ret, block);
      return 1;
    }
    
    if (ret == acked + 1) {
      acked++;
      fprintf(stderr, "write block %d, size %ld\n", acked, block_size);
        ret = fwrite(block,block_size,1, fp);
        if (ret < 0) {
          perror("fwrite");
          return 1;
        }
    } 
    // `atftp` sends an extra ACK on first duplicate DATA, ignore further extra ACKs.
    // `tftp-hpa` always sends current ACK.

ack:
    len = tftp_build_ack(buf, 1024, acked);
    ret = send(sfd, buf, len, 0);
    if (ret < 0) {
      perror("send");
      return 1;
    }
  } while (block_size == 512);
  free(buf);
  return 0;
}