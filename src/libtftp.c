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

#define OACK 6

int tftp_build_rrq(char *buf, int n, char *filename, short window) {
  (*(struct tftphdr *)buf).th_opcode = htons(RRQ);

  size_t len = strlen(filename);
  char *p = buf + offsetof(struct tftphdr, th_u1);
  strcpy(p, filename);
  p += len+1;

  strcpy(p, "octet");
  p += sizeof("octet");

  if (window) {
    strcpy(p, "windowsize");
    p += sizeof("windowsize");

    char n_blocks[10];
    sprintf(n_blocks, "%d", window);
    strcpy(p, n_blocks);
    p += strlen(n_blocks) + 1;
  }

  return p - buf;
}

int tftp_parse_response(char *buf, int n, char **block, size_t *block_size) {
  struct tftphdr *hdr = (struct tftphdr *)buf;
  short opcode = ntohs(hdr->th_opcode);
  if (opcode == DATA) {
    *block = hdr->th_u1.th_u2.tu_data;
    *block_size = n - 4;
    int block_id = ntohs(hdr->th_u1.th_u2.th_u3.tu_block);
    //fprintf(stderr, "block %d: %ld bytes\n", block_id, *block_size);
    return ntohs(hdr->th_u1.th_u2.th_u3.tu_block);
  } else if (opcode == ERROR) {
    *block = hdr->th_u1.th_u2.tu_data;
    *block_size = n - 4;
    return -ntohs(hdr->th_u1.th_u2.th_u3.tu_code);
  } else {
    *block = "unknown opcode";
    *block_size = sizeof("unknown opcode");
    return -1;
  }
}

int tftp_parse_oack(char *buf, int n, char **error) {
  struct tftphdr *hdr = (struct tftphdr *)buf;
  short opcode = ntohs(hdr->th_opcode);
  short window;
  if (opcode == OACK) {
    char extension[12];
    if (sscanf(buf + offsetof(struct tftphdr, th_u1),"%s", extension) != 1) {
      *error = "invalid extension name";
      return -9;
    }
    if (strcmp(extension, "windowsize")) {
      *error = "not windowsize extension";
      return 0;
    }
    if (sscanf(buf + offsetof(struct tftphdr, th_u1) + strlen(extension) + 1, "%hd", &window) != 1) {
      *error = "malformed window size";
      return 0;
    }
    return window;
  } else if (opcode == ERROR) {
    *error = hdr->th_u1.th_u2.tu_data;
    return -ntohs(hdr->th_u1.th_u2.th_u3.tu_code);
  } else {
    *error = "unknown opcode in OACK response";
    return -1;
  }
}

int tftp_build_ack(char *buf, int len, int n) {
  struct tftphdr *p = (struct tftphdr *)buf;
  p->th_opcode = htons(ACK);
  p->th_u1.th_u2.th_u3.tu_block = htons(n);
  return 2 * sizeof(short);
}