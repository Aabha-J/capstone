// Simple electrical link baseline between two logical chiplets.
// This is a clocked FPGA model, not a physical chiplet wire.
module chiplet_link #(
    parameter integer DATA_W = 16,
    parameter integer LINK_CYCLES = 2
)(
    input  wire              clk,
    input  wire              reset_n,
    input  wire              tx_valid,
    input  wire [DATA_W-1:0] tx_data,
    output wire              tx_ready,
    output wire              rx_valid,
    output wire [DATA_W-1:0] rx_data,
    input  wire              rx_ready
);
    // One packet can be in flight at a time for the first demo.
    reg busy;
    reg [DATA_W-1:0] saved_data;
    reg [31:0] remaining;
    reg out_valid;
    reg [DATA_W-1:0] out_data;

    assign tx_ready = !busy && !out_valid;
    assign rx_valid = out_valid;
    assign rx_data = out_data;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            busy <= 1'b0;
            saved_data <= {DATA_W{1'b0}};
            remaining <= 32'd0;
            out_valid <= 1'b0;
            out_data <= {DATA_W{1'b0}};
        end else begin
            if (out_valid && rx_ready)
                out_valid <= 1'b0;

            if (tx_valid && tx_ready) begin
                saved_data <= tx_data;
                remaining <= LINK_CYCLES;
                busy <= 1'b1;
            end else if (busy) begin
                if (remaining > 1)
                    remaining <= remaining - 1'b1;
                else begin
                    out_data <= saved_data;
                    out_valid <= 1'b1;
                    busy <= 1'b0;
                end
            end
        end
    end
endmodule
