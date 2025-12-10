#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/ip_icmp.h>
#include <arpa/tftp.h>
#include <resolv.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
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

  return 1;
}