#include <stdio.h>

// This code may not work with platform with does not allow unaligned access.
// 
// See: https://www.kernel.org/doc/html/v6.18/core-api/unaligned-memory-access.html

/**
  @brief Generate TFTP RRQ, optionally with window size.

  @param[in] buf packet
  @param[in] n packet length
  @param[in] filename
  @param[in] window window size, 0 to disable.

  @return : actual packet length
 */
int tftp_build_rrq(char *buf, int n, char *filename, short window);

/**
  @brief Parse data packet from server

  @param[in] buf packet
  @param[in] n packet length
  @param[out] block pointer to data/error message in packet, NULL on invalid packet
  @param[out] block_size length of data/error message

  @return positive value for seqno on success, negative value for negated error code.
 */
int tftp_parse_response(char *buf, int n, char **block, size_t *block_size);

/**
  @brief Parse OACK from server, for actual window size.

  @param[in] buf packet
  @param[in] n packet length
  @param[out] error pointer to error message in packet

  @return positive value for server-side window on success, negative value for negated error code.
 */
int tftp_parse_oack(char *buf, int n, char **error);

/**
  @brief Build ACK packet

  @param[in] buf packer buffer
  @param[in] len buffer size
  @param[out] n seqno to ACK

  @return packet size
 */
int tftp_build_ack(char *buf, int len, int n);

int tftp_loop(int sfd, FILE *fp, short window);